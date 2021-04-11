from sqlalchemy.types import TypeDecorator, String
from citext import CIText


class CaseInsensitiveString(TypeDecorator):

    impl = String

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(CIText())
        else:
            return dialect.type_descriptor(self.impl)
