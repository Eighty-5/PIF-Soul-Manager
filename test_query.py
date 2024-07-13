from myproject.models import Pokedex, PokedexStats, Sprite, Artist
from myproject.extensions import db
from myproject import create_app

app = create_app()

def main() -> None:
    with app.app_context():
        result = db.session.execute(db.select(Pokedex).where(Pokedex.number=="200.200")).scalar()
        print(result.head.fusions_body)


if __name__ == "__main__":
    main()