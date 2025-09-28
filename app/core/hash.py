import bcrypt

class Hasher():
    @staticmethod
    def verify_password(plain_password, hashed_password):
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    @staticmethod
    def get_password_hash(password):
        # convert password to bytes
        bytes = password.encode('utf-8')
        # hash the password
        hashed = bcrypt.hashpw(bytes, bcrypt.gensalt())

        return hashed.decode('utf-8')