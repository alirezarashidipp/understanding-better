from api import create_app

app = create_app()


if __name__ == "__main__":
    from cli import main

    main(app_path="main:app", factory=False)
