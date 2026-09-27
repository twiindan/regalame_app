import json
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from catalog import _parse_price, extract_asin, list_categories, normalize_text, slugify
from models import Product, ProductList


def test_product_and_productlist_roundtrip(session):
    product = Product(
        asin="B0049U0DMC",
        title="Lavazza Qualità Oro",
        title_normalized="lavazza qualita oro",
        image_url="https://img.example/1.jpg",
        url="https://www.amazon.es/dp/B0049U0DMC",
        category="Alimentación y bebidas",
        category_slug="alimentacion-y-bebidas",
        price_numeric=25.69,
        price_raw="25,69 €",
        scraped_at=datetime(2026, 9, 1),
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    link = ProductList(product_id=product.id, list_key="bestsellers", rank=1)
    session.add(link)
    session.commit()

    stored = session.exec(select(Product).where(Product.asin == "B0049U0DMC")).first()
    assert stored is not None
    assert stored.title_normalized == "lavazza qualita oro"
    assert stored.price_numeric == 25.69
    assert stored.is_active is True
    assert stored.updated_at is not None

    stored_link = session.exec(select(ProductList).where(ProductList.list_key == "bestsellers")).first()
    assert stored_link is not None
    assert stored_link.product_id == product.id
    assert stored_link.rank == 1


def test_productlist_unique_per_product_and_list(session):
    product = Product(
        asin="X1",
        title="T",
        title_normalized="t",
        url="https://www.amazon.es/dp/X1",
        category="Varios",
        category_slug="varios",
        scraped_at=datetime(2026, 9, 1),
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    session.add(ProductList(product_id=product.id, list_key="trends", rank=1))
    session.commit()
    session.add(ProductList(product_id=product.id, list_key="trends", rank=2))
    with pytest.raises(IntegrityError):
        session.commit()


def test_normalize_text_lowercases_and_strips_accents():
    assert normalize_text("Café") == "cafe"
    assert normalize_text("  Alimentación y Bebidas ") == "alimentacion y bebidas"
    assert normalize_text(None) == ""


def test_slugify_matches_existing_behavior():
    assert slugify("Hogar y cocina") == "hogar-y-cocina"
    assert slugify("Alimentación y bebidas") == "alimentacion-y-bebidas"


def test_extract_asin_from_dp_url():
    assert extract_asin("https://www.amazon.es/Lavazza-1kg/dp/B0049U0DMC/ref=zg_bs?psc=1") == "B0049U0DMC"


def test_extract_asin_from_gp_product_url():
    assert extract_asin("https://www.amazon.es/gp/product/B085LCQNZV?ref=x") == "B085LCQNZV"


def test_extract_asin_fallback_is_stable_and_distinct():
    a = extract_asin("https://www.amazon.es/algo-sin-asin/ref=x")
    b = extract_asin("https://www.amazon.es/algo-sin-asin/ref=x")
    c = extract_asin("https://www.amazon.es/otra-cosa/ref=x")
    assert a == b
    assert a.startswith("h")
    assert a != c


def test_parse_price_european_comma():
    assert _parse_price("19,99 €") == 19.99


def test_parse_price_eur_prefix():
    assert _parse_price("EUR 20.50") == 20.5


def test_parse_price_european_thousands():
    assert _parse_price("1.234,56") == 1234.56


def test_parse_price_non_numeric_returns_zero():
    assert _parse_price("N/A") == 0.0
    assert _parse_price(None) == 0.0


def test_parse_price_range_returns_zero():
    """Range prices are intentionally non-convertible -> mapped to None by the import."""
    assert _parse_price("13,99 € - 17,99 €") == 0.0
    assert _parse_price("7,91 €\xa0-\xa019,99 €") == 0.0


from catalog import CatalogResult, CatalogQuery, search_products


def test_search_by_text_is_accent_and_case_insensitive(session, catalog_seed):
    result = search_products(session, CatalogQuery(q="CAFE"))
    assert result.total == 2


def test_search_ignores_terms_shorter_than_two_chars(session, catalog_seed):
    result = search_products(session, CatalogQuery(q="a"))
    assert result.total == 3


def test_filter_by_category_slug(session, catalog_seed):
    result = search_products(session, CatalogQuery(category_slug="electronica"))
    assert result.total == 1
    assert result.items[0].asin == "B1"


def test_filter_by_source_uses_product_list(session, catalog_seed):
    result = search_products(session, CatalogQuery(source="trends"))
    assert result.total == 2
    assert {p.asin for p in result.items} == {"A2", "B1"}


def test_price_range_excludes_null_prices(session, catalog_seed):
    result = search_products(session, CatalogQuery(min_price=1.0, max_price=200.0))
    assert result.total == 2
    assert all(p.price_numeric is not None for p in result.items)


def test_min_price_greater_than_max_is_swapped(session, catalog_seed):
    result = search_products(session, CatalogQuery(min_price=200.0, max_price=1.0))
    assert result.total == 2


def test_filters_combine(session, catalog_seed):
    result = search_products(session, CatalogQuery(source="bestsellers", category_slug="alimentacion-y-bebidas"))
    assert result.total == 2
    result = search_products(session, CatalogQuery(source="trends", category_slug="alimentacion-y-bebidas"))
    assert result.total == 1
    assert result.items[0].asin == "A2"


def test_sort_price_asc_puts_nulls_last(session, catalog_seed):
    result = search_products(session, CatalogQuery(sort="price_asc"))
    assert [p.asin for p in result.items] == ["A1", "A2", "B1"]


def test_sort_price_desc_puts_nulls_last(session, catalog_seed):
    result = search_products(session, CatalogQuery(sort="price_desc"))
    assert [p.asin for p in result.items] == ["A2", "A1", "B1"]


def test_sort_newest_orders_by_scraped_at_desc(session, catalog_seed):
    result = search_products(session, CatalogQuery(sort="newest"))
    assert [p.asin for p in result.items] == ["A2", "B1", "A1"]


def test_sort_random_returns_all_items(session, catalog_seed):
    result = search_products(session, CatalogQuery(sort="random"))
    assert result.total == 3
    assert len(result.items) == 3


def test_relevance_with_query_prioritizes_prefix_matches(session, catalog_seed):
    result = search_products(session, CatalogQuery(q="cafe"))
    assert result.items[0].asin == "A1"


def test_relevance_without_query_uses_rank(session, catalog_seed):
    result = search_products(session, CatalogQuery(source="bestsellers"))
    assert [p.asin for p in result.items] == ["A1", "A2"]


def test_pagination_reports_total_and_total_pages(session, catalog_seed):
    result = search_products(session, CatalogQuery(per_page=2, page=1))
    assert isinstance(result, CatalogResult)
    assert result.total == 3
    assert result.total_pages == 2
    assert len(result.items) == 2

    page2 = search_products(session, CatalogQuery(per_page=2, page=2))
    assert len(page2.items) == 1


def test_per_page_is_capped_at_60(session, catalog_seed):
    result = search_products(session, CatalogQuery(per_page=500))
    assert result.per_page == 60


def test_page_out_of_range_clamps_to_last(session, catalog_seed):
    result = search_products(session, CatalogQuery(per_page=2, page=99))
    assert result.page == 2


def test_page_below_one_clamps_to_first(session, catalog_seed):
    result = search_products(session, CatalogQuery(page=0))
    assert result.page == 1


def test_pagination_is_stable_across_pages_for_ties(session):
    from datetime import datetime
    from models import Product

    session.add_all([
        Product(asin=f"T{i}", title=f"Producto {i}", title_normalized=f"producto {i}",
                url=f"https://www.amazon.es/dp/T{i}", category="Varios", category_slug="varios",
                price_numeric=None, price_raw="N/A", scraped_at=datetime(2026, 1, 1))
        for i in range(5)
    ])
    session.commit()

    seen = []
    page = 1
    while True:
        result = search_products(session, CatalogQuery(per_page=2, page=page))
        seen.extend(p.asin for p in result.items)
        if page >= result.total_pages:
            break
        page += 1

    assert sorted(seen) == ["T0", "T1", "T2", "T3", "T4"]
    assert len(seen) == len(set(seen))  # no duplicates across pages


def test_relevance_with_query_prioritizes_prefix_over_better_rank(session):
    from datetime import datetime
    from models import Product, ProductList

    mid = Product(asin="M1", title="Gran Café molido", title_normalized="gran cafe molido",
                  url="https://www.amazon.es/dp/M1", category="Varios", category_slug="varios",
                  price_numeric=None, price_raw="N/A", scraped_at=datetime(2026, 1, 1))
    pre = Product(asin="P1", title="Café molido", title_normalized="cafe molido",
                  url="https://www.amazon.es/dp/P1", category="Varios", category_slug="varios",
                  price_numeric=None, price_raw="N/A", scraped_at=datetime(2026, 1, 1))
    session.add_all([mid, pre]); session.commit()
    session.refresh(mid); session.refresh(pre)
    session.add_all([
        ProductList(product_id=mid.id, list_key="bestsellers", rank=1),
        ProductList(product_id=pre.id, list_key="bestsellers", rank=2),
    ]); session.commit()

    result = search_products(session, CatalogQuery(q="cafe", source="bestsellers"))
    assert [p.asin for p in result.items] == ["P1", "M1"]


def test_search_treats_like_wildcards_literally(session, catalog_seed):
    assert search_products(session, CatalogQuery(q="__")).total == 0
    assert search_products(session, CatalogQuery(q="a_")).total == 0


def test_list_categories_returns_name_slug_pairs_sorted(session, catalog_seed):
    cats = list_categories(session)
    assert cats == [
        ("Alimentación y bebidas", "alimentacion-y-bebidas"),
        ("Electrónica", "electronica"),
    ]


def test_list_categories_excludes_inactive_products(session):
    from datetime import datetime
    from models import Product

    session.add(Product(asin="off", title="Off", title_normalized="off",
                        url="https://www.amazon.es/dp/off", category="Oculta", category_slug="oculta",
                        scraped_at=datetime(2026, 1, 1), is_active=False))
    session.commit()
    assert list_categories(session) == []


def test_list_categories_sorts_accented_names_insensitively(session):
    from datetime import datetime
    from models import Product

    session.add_all([
        Product(asin="Z1", title="Ámbar", title_normalized="ambar",
                url="https://www.amazon.es/dp/Z1", category="Ámbar", category_slug="ambar",
                scraped_at=datetime(2026, 1, 1)),
        Product(asin="Z2", title="Bicicletas", title_normalized="bicicletas",
                url="https://www.amazon.es/dp/Z2", category="Bicicletas", category_slug="bicicletas",
                scraped_at=datetime(2026, 1, 1)),
    ])
    session.commit()

    # Raw SQLite BINARY collation would put "Bicicletas" first (B < Á by byte), so this
    # pins the accent-insensitive Python sort.
    assert [slug for _, slug in list_categories(session)] == ["ambar", "bicicletas"]


from catalog import import_from_json


def _write_json(tmp_path, name, items):
    path = tmp_path / name
    path.write_text(json.dumps(items), encoding="utf-8")
    return str(path)


def _raw_item(asin, title, category, price):
    return {
        "title": title,
        "category": category,
        "price": price,
        "image": f"img-{asin}.jpg",
        "url": f"https://www.amazon.es/dp/{asin}/ref=x",
    }


def test_import_creates_products_and_list_ranks(session, tmp_path):
    files = {"bestsellers": _write_json(tmp_path, "b.json", [
        _raw_item("A100000001", "Café molido", "Alimentación y bebidas", "10,00 €"),
        _raw_item("A200000002", "Cafetera", "Alimentación y bebidas", "100,50 €"),
    ])}
    stats = import_from_json(session, data_files=files)
    assert stats["created"] == 2

    from models import Product, ProductList
    assert session.exec(select(Product)).all().__len__() == 2

    rows = session.exec(select(ProductList).order_by(ProductList.rank)).all()
    assert [r.rank for r in rows] == [1, 2]

    a1 = session.exec(select(Product).where(Product.asin == "A100000001")).first()
    assert a1.title_normalized == "cafe molido"
    assert a1.category_slug == "alimentacion-y-bebidas"
    assert a1.price_numeric == 10.0
    assert a1.price_raw == "10,00 €"


def test_import_marks_unparseable_price_as_none(session, tmp_path):
    from models import Product
    files = {"trends": _write_json(tmp_path, "t.json", [
        _raw_item("N100000003", "Sin precio", "Varios", "N/A"),
    ])}
    import_from_json(session, data_files=files)
    product = session.exec(select(Product).where(Product.asin == "N100000003")).first()
    assert product.price_numeric is None
    assert product.price_raw == "N/A"


def test_import_is_idempotent(session, tmp_path):
    from models import Product, ProductList
    files = {"bestsellers": _write_json(tmp_path, "b.json", [
        _raw_item("A100000001", "Café", "Alimentación y bebidas", "10,00 €"),
        _raw_item("A200000002", "Cafetera", "Alimentación y bebidas", "100,50 €"),
    ])}
    import_from_json(session, data_files=files)
    counts = (
        len(session.exec(select(Product)).all()),
        len(session.exec(select(ProductList)).all()),
    )

    import_from_json(session, data_files=files)
    counts_again = (
        len(session.exec(select(Product)).all()),
        len(session.exec(select(ProductList)).all()),
    )
    assert counts == counts_again == (2, 2)


def test_import_dry_run_does_not_write(session, tmp_path):
    from models import Product
    files = {"bestsellers": _write_json(tmp_path, "b.json", [
        _raw_item("A100000001", "Café molido", "Alimentación y bebidas", "10,00 €"),
    ])}
    stats = import_from_json(session, data_files=files, dry_run=True)
    assert stats["created"] == 1
    assert session.exec(select(Product)).all() == []


def test_extract_asin_does_not_truncate_longer_token():
    # A 11-char token after /dp/ is not a valid ASIN -> falls back to the path hash
    result = extract_asin("https://www.amazon.es/dp/B0049U0DMCX/ref=x")
    assert result != "B0049U0DMC"
    assert result.startswith("h")


def test_import_dedupes_repeated_asin_within_a_list(session, tmp_path):
    from models import Product, ProductList
    files = {"bestsellers": _write_json(tmp_path, "b.json", [
        _raw_item("A100000001", "Café", "Alimentación y bebidas", "10,00 €"),
        _raw_item("A100000001", "Café", "Belleza", "10,00 €"),
    ])}
    stats = import_from_json(session, data_files=files)
    assert stats["created"] == 1
    assert len(session.exec(select(Product)).all()) == 1
    links = session.exec(select(ProductList).where(ProductList.list_key == "bestsellers")).all()
    assert len(links) == 1
    assert links[0].rank == 1


def test_import_product_shared_across_lists_creates_two_links(session, tmp_path):
    from models import Product, ProductList
    files = {
        "bestsellers": _write_json(tmp_path, "b.json", [_raw_item("A100000001", "Café", "Varios", "10,00 €")]),
        "trends": _write_json(tmp_path, "t.json", [_raw_item("A100000001", "Café", "Varios", "10,00 €")]),
    }
    import_from_json(session, data_files=files)
    assert len(session.exec(select(Product)).all()) == 1
    links = session.exec(select(ProductList)).all()
    assert {link.list_key for link in links} == {"bestsellers", "trends"}
    assert len(links) == 2


def test_import_untouched_list_is_not_wiped_by_empty_file(session, tmp_path):
    from models import Product, ProductList
    files = {"bestsellers": _write_json(tmp_path, "b.json", [_raw_item("A100000001", "Café", "Varios", "10,00 €")])}
    import_from_json(session, data_files=files)
    assert len(session.exec(select(ProductList)).all()) == 1

    import_from_json(session, data_files={"bestsellers": _write_json(tmp_path, "empty.json", [])})
    from models import Product as P
    assert len(session.exec(select(Product)).all()) == 1
