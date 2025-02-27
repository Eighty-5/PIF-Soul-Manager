from pifsm import create_app
import time
from pifsm.decorators import func_timer
from pifsm.models import *


app = create_app()

@func_timer
def main(*args, **kwargs) -> None:
    with app.app_context():
        stmt_1 = ~db.select(Family).join(Family.evolutions).exists()
        # result = db.session.scalars(db.select(Family).where(~stmt)).all()
        # print(len(result))
        stmt_2 = db.select(Family).where(Family.evolutions==None)
        print(stmt_1)
        print("\n")
        print(stmt_2)

        # result = db.session.scalars(db.select(Family)).all()
        # print(len(result))
        result = db.session.scalars(db.select(Family).where(Family.evolutions==None))
        for item in result:
            print(item)

if __name__ == "__main__":
    main()