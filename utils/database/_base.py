import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session

BaseClass = orm.declarative_base()

__factory = None

sess = None

def global_init(db_file = 'storage/base.db'):
    global __factory

    if __factory:
        return

    if not db_file or not db_file.strip():
        raise Exception("Необходимо указать файл базы данных.")

    conn_str = f'sqlite:///{db_file.strip()}?check_same_thread=False'

    engine = sa.create_engine(conn_str, echo=False)
    __factory = orm.sessionmaker(bind=engine)

    from . import __all_models

    BaseClass.metadata.create_all(engine)


def create_session() -> Session:
    global __factory, sess
    if __factory is None:
        global_init()
    if sess is None:
        sess = __factory()
    return sess