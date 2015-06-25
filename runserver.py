from flask_failsafe import failsafe

@failsafe
def create_app():
    from karaokeindex import app
    return app

if __name__ == "__main__":
    create_app().run(debug=True)
