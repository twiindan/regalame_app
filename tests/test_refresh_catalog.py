"""Catalog refresh orchestration: health classification and failure containment."""

import json
import os
from datetime import datetime

from sqlmodel import func, select

import jobs.refresh_catalog as refresh_catalog
from models import Product, ProductList
from scraper import SECTIONS

FILENAMES = {section.list_key: section.filename for section in SECTIONS}
FULL = {"bestsellers": 12, "trends": 12, "desired": 12}


def product_json(list_key, index, title=None):
    asin = f"B{list_key[:2].upper()}{index:07d}"
    return {"category": "Electrónica", "title": title or f"Producto {list_key} {index}",
            "image": f"https://img/{asin}.jpg",
            "url": f"https://www.amazon.es/dp/{asin}", "price": "19,99 €"}


def fake_scrape(counts):
    """A scrape_fn writing `counts[list_key]` items; None means the section failed."""
    def _scrape(out_dir):
        produced = {}
        for list_key, count in counts.items():
            if count is None:
                continue
            path = os.path.join(out_dir, FILENAMES[list_key])
            with open(path, "w", encoding="utf-8") as handle:
                json.dump([product_json(list_key, i) for i in range(count)], handle)
            produced[list_key] = path
        return produced
    return _scrape


def silent(*args, **kwargs):
    pass


def snapshot_catalog(session):
    products = sorted(tuple(row) for row in session.exec(
        select(Product.id, Product.title, Product.is_active, Product.updated_at)).all())
    lists = sorted(tuple(row) for row in session.exec(
        select(ProductList.product_id, ProductList.list_key, ProductList.rank)).all())
    return products, lists


def test_baseline_counts_reads_each_list(session, catalog_seed):
    """The health reference comes from the DB, so no new state is needed."""
    assert refresh_catalog.baseline_counts(session) == {"bestsellers": 2, "trends": 2}


def test_a_healthy_section_passes_the_guard(tmp_path):
    good = tmp_path / "good.json"
    good.write_text(json.dumps([product_json("bestsellers", i) for i in range(12)]),
                    encoding="utf-8")

    healthy, suspicious = refresh_catalog.classify(
        {"bestsellers": str(good)}, {"bestsellers": 12})

    assert set(healthy) == {"bestsellers"}
    assert suspicious == []


def test_a_truncated_section_is_suspicious(tmp_path):
    """Amazon returning 200 with a partial grid must not be taken as truth."""
    short = tmp_path / "short.json"
    short.write_text(json.dumps([product_json("bestsellers", i) for i in range(4)]),
                     encoding="utf-8")

    healthy, suspicious = refresh_catalog.classify(
        {"bestsellers": str(short)}, {"bestsellers": 20})

    assert healthy == {}
    assert suspicious == ["bestsellers"]


def test_a_missing_file_is_suspicious():
    healthy, suspicious = refresh_catalog.classify(
        {"bestsellers": "/nonexistent/none.json"}, {})

    assert healthy == {}
    assert suspicious == ["bestsellers"]


def test_an_unreadable_file_is_suspicious(tmp_path):
    bad = tmp_path / "broken.json"
    bad.write_text("{not json", encoding="utf-8")

    healthy, suspicious = refresh_catalog.classify({"bestsellers": str(bad)}, {})

    assert healthy == {}
    assert suspicious == ["bestsellers"]


def test_a_first_run_has_no_reference_to_fall_short_of(tmp_path):
    """An empty DB must not make every section suspicious."""
    first = tmp_path / "first.json"
    first.write_text(json.dumps([product_json("bestsellers", 0)]), encoding="utf-8")

    healthy, suspicious = refresh_catalog.classify({"bestsellers": str(first)}, {})

    assert set(healthy) == {"bestsellers"}
    assert suspicious == []


def test_a_healthy_run_imports_every_section(session):
    code = refresh_catalog.run(session, scrape_fn=fake_scrape(FULL), log=silent)

    assert code == 0
    assert session.exec(select(func.count()).select_from(Product)).one() == 36
    assert set(session.exec(select(ProductList.list_key)).all()) == set(FULL)


def test_a_failed_section_keeps_its_ranks(session):
    ghost = Product(asin="GHOSTGHOST", title="Sólo en trends", title_normalized="solo en trends",
                    image_url=None, url="https://www.amazon.es/dp/GHOSTGHOST",
                    category="Varios", category_slug="varios",
                    price_numeric=None, price_raw="N/A", scraped_at=datetime(2026, 1, 1))
    session.add(ghost)
    session.commit()
    session.refresh(ghost)
    session.add(ProductList(product_id=ghost.id, list_key="trends", rank=7))
    session.commit()

    code = refresh_catalog.run(
        session, scrape_fn=fake_scrape(dict(FULL, trends=None)), log=silent)

    assert code == 0
    rows = session.exec(select(ProductList).where(ProductList.list_key == "trends")).all()
    assert [(row.product_id, row.rank) for row in rows] == [(ghost.id, 7)]


def test_a_failed_section_is_not_handed_to_the_import(session, monkeypatch):
    captured = {}
    real_import = refresh_catalog.import_from_json

    def spy(session, data_files=None, dry_run=False):
        captured["keys"] = sorted(data_files or {})
        return real_import(session, data_files=data_files, dry_run=dry_run)

    monkeypatch.setattr(refresh_catalog, "import_from_json", spy)

    refresh_catalog.run(session, scrape_fn=fake_scrape(dict(FULL, trends=None)), log=silent)

    assert captured["keys"] == ["bestsellers", "desired"]


def test_a_truncated_section_is_excluded_from_the_import(session):
    """The DB-level counterpart of the classify unit tests."""
    refresh_catalog.run(
        session, scrape_fn=fake_scrape({"bestsellers": 20, "trends": 20, "desired": 20}),
        log=silent)
    refresh_catalog.run(
        session, scrape_fn=fake_scrape({"bestsellers": 4, "trends": 20, "desired": 20}),
        log=silent)

    rows = session.exec(select(ProductList).where(ProductList.list_key == "bestsellers")).all()
    assert len(rows) == 20  # untouched: the 4-item section was rejected


def test_a_run_with_no_healthy_section_writes_nothing(session):
    refresh_catalog.run(session, scrape_fn=fake_scrape(FULL), log=silent)
    before = snapshot_catalog(session)

    code = refresh_catalog.run(
        session,
        scrape_fn=fake_scrape({"bestsellers": None, "trends": None, "desired": None}),
        log=silent)

    assert code == 1
    assert snapshot_catalog(session) == before


def test_the_exit_code_is_zero_when_only_some_sections_survive(session):
    code = refresh_catalog.run(
        session, scrape_fn=fake_scrape(dict(FULL, desired=None)), log=silent)
    assert code == 0


def test_data_dir_never_invokes_the_scraper(session, tmp_path):
    for list_key, count in FULL.items():
        (tmp_path / FILENAMES[list_key]).write_text(
            json.dumps([product_json(list_key, i) for i in range(count)]), encoding="utf-8")

    def exploding(out_dir):
        raise AssertionError("the scraper must not run with --data-dir")

    code = refresh_catalog.run(session, scrape_fn=exploding, data_dir=str(tmp_path), log=silent)
    assert code == 0
    assert session.exec(select(func.count()).select_from(Product)).one() == 36


def test_dry_run_writes_nothing(session, tmp_path):
    for list_key, count in FULL.items():
        (tmp_path / FILENAMES[list_key]).write_text(
            json.dumps([product_json(list_key, i) for i in range(count)]), encoding="utf-8")

    code = refresh_catalog.run(session, data_dir=str(tmp_path), dry_run=True, log=silent)
    assert code == 0
    assert session.exec(select(func.count()).select_from(Product)).one() == 0


def test_main_reports_the_run(session, tmp_path, capsys):
    for list_key, count in FULL.items():
        (tmp_path / FILENAMES[list_key]).write_text(
            json.dumps([product_json(list_key, i) for i in range(count)]), encoding="utf-8")

    code = refresh_catalog.main(["--data-dir", str(tmp_path)], session=session)

    assert code == 0
    assert "sections_ok=3" in capsys.readouterr().out


def test_the_default_scrape_fn_awaits_the_real_async_scraper(session, monkeypatch):
    """The injected fakes are synchronous; the production scraper is a coroutine.

    No other test exercises the default ``scrape_fn``, so without this the whole
    unattended path could ship handing a coroutine object to ``classify``.
    """
    async def fake_async_scrape(out_dir):
        path = os.path.join(out_dir, FILENAMES["bestsellers"])
        with open(path, "w", encoding="utf-8") as handle:
            json.dump([product_json("bestsellers", i) for i in range(12)], handle)
        return {"bestsellers": path}

    monkeypatch.setattr(refresh_catalog, "scrape_all", fake_async_scrape)

    code = refresh_catalog.run(session, log=silent)

    assert code == 0
    assert session.exec(select(func.count()).select_from(Product)).one() == 12
