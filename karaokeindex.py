from flask import Flask, render_template, abort, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy
from sqlalchemy.ext.hybrid import hybrid_property
import os
import re
from unidecode import unidecode
from icu import Locale, Collator

app = Flask(__name__)

app.config.update(dict(
    SQLALCHEMY_DATABASE_URI='sqlite:///' +
    os.path.join(app.root_path, 'karaokeindex.db'),
    SQLALCHEMY_ECHO=False,
    KARAOKE_DIR='/Volumes/Stuff/Karaoke'
))

app.jinja_env.trim_blocks = True

db = SQLAlchemy(app)

relationship_table = db.Table('relationship_table',
    db.Column('artist_id', db.Integer, db.ForeignKey('artists.id'), nullable=False),
    db.Column('song_id', db.Integer, db.ForeignKey('songs.id'), nullable=False),
    db.PrimaryKeyConstraint('artist_id', 'song_id')
)

def regexp(expr, item):
    item = unidecode(item)
    reg = re.compile(r'^(?:\([^\(\)]+\) )?(?:[^a-zA-Z0-9]+)?(.).*')
    first_char = reg.match(item).group(1).lower()
    if expr.isdigit():
        return first_char.isdigit()
    else:
        return first_char == expr

@db.event.listens_for(db.engine, "begin")
def do_begin(conn):
    conn.connection.create_function('REGEXP', 2, regexp)

class Artist(db.Model):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.Text, nullable=False, unique=True)
    songs = db.relationship('Song', secondary=relationship_table, backref=db.backref('artists', lazy='dynamic'))

    def __repr__(self):
        return '<Artist "%s">' % (self.name, )

    @hybrid_property
    def starts_with_num(self):
        return self.name[0].isdigit()

class Song(db.Model):
    __tablename__ = 'songs'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    title = db.Column(db.Text, nullable=False, unique=True)
    sort = db.Column(db.Text, nullable=False, default=False)
    is_alias = db.Column(db.Boolean)

    def __repr__(self):
        return '<Song "%s">' % (self.title, )

    @hybrid_property
    def first_character(self):
        title = unidecode(self.title)
        reg = re.compile(r'^(?:\([^\(\)]+\) )?(?:[^a-zA-Z0-9]+)?(.*)')

        return reg.match(title).group(1)[0]

@app.route('/')
def root():
    return redirect(url_for('artists_index', start='a'))


@app.route('/<start>/')
def artists_index(start):
    if len(start) > 1 and start != "0-9":
        abort(404)

    if start.lower() != start:
        return redirect(url_for('artists_index', start=start.lower()))

    if start == "0-9":
        artists = Artist.query.filter(Artist.name.op('REGEXP')('1')).all()
    else:
        artists = Artist.query.filter(Artist.name.op('REGEXP')(start)).all()

    return render_template('index.html', type='artists', artists=artists, start=start.upper())

@app.route('/songs/')
def songs():
    return redirect(url_for('songs_index', start='a'))

@app.route('/songs/<start>/')
def songs_index(start):
    if len(start) > 1 and start != "0-9":
        abort(404)

    if start.lower() != start:
        return redirect(url_for('songs_index', start=start.lower()))

    if start == "0-9":
        songs = Song.query.filter(Song.title.op('REGEXP')('1')).all()
    else:
        songs = Song.query.filter(Song.title.op('REGEXP')(start)).all()

    songs = sorted(songs, key=lambda song: song.sort)

    return render_template('index.html', type='songs', songs=songs, start=start.upper())


if __name__ == '__main__':
    app.run()
