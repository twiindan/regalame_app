import bcrypt


def get_password_hash(password: str) -> str:
    """
    Recibe una contraseña en texto plano y devuelve el hash seguro.
    Bcrypt tiene un límite de 72 bytes, así que truncamos si es necesario.
    """
    # 1. Recortar a 72 caracteres para evitar el error de ValueError
    short_pwd = password[:72]

    # 2. Convertir a bytes (utf-8)
    pwd_bytes = short_pwd.encode('utf-8')

    # 3. Generar la sal (salt) y hashear
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)

    # 4. Devolver como string para guardarlo en la base de datos
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si la contraseña plana coincide con el hash guardado.
    """
    # 1. Recortar la contraseña entrante igual que al crearla
    short_pwd = plain_password[:72]

    # 2. Convertir ambos a bytes
    pwd_bytes = short_pwd.encode('utf-8')
    # Asegurarnos de que el hash guardado sea bytes
    hashed_bytes = hashed_password.encode('utf-8')

    # 3. Verificar
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except ValueError:
        # Si el formato del hash es inválido
        return False