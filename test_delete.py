from myproject.models import Pokedex, PokedexStats, Sprite, Artist, Pokemon, Route
from myproject.extensions import db
from myproject import create_app
from sqlalchemy import delete
import datetime
import time

import csv

app = create_app()

def main() -> None:
    with app.app_context():
        
        time0 = time.perf_counter()

        # test_1

        db.session.execute(db.delete(Route))
        db.session.execute(db.delete(Pokemon))
        db.session.execute(db.delete(Sprite))
        db.session.execute(db.delete(Artist))
        db.session.execute(db.delete(PokedexStats))
        db.session.execute(db.delete(Pokedex).where(Pokedex.head!=None))
        db.session.execute(db.delete(Pokedex))
        db.session.commit()

        time1 = time.perf_counter()
        print(time1 - time0)

if __name__ == '__main__':
    main()