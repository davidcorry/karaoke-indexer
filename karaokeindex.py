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
    files = db.relationship('SongFile', backref='artist', lazy='dynamic')
    _songs = db.relationship('Song', secondary="songfiles", backref=db.backref('artists', lazy='dynamic'))
    _song_aliases = db.relationship('SongAlias', backref='artist', lazy='dynamic')

    def _get_songs(self):
        return self._songs + self._song_aliases.all()
    songs = property(_get_songs)

    def __repr__(self):
        return '<Artist "%s">' % (self.name, )

    @hybrid_property
    def starts_with_num(self):
        return self.name[0].isdigit()

class Song(db.Model):
    __tablename__ = 'songs'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    title = db.Column(db.Text, nullable=False, unique=True)
    sort = db.Column(db.Text, nullable=False)
    aliases = db.relationship('SongAlias', backref='song', lazy='dynamic')
    files = db.relationship('SongFile', backref='song', lazy='dynamic')
    is_alias = db.Column(db.Boolean)

    def __repr__(self):
        return '<Song title "%s">' % (self.title, )

    @hybrid_property
    def first_character(self):
        title = unidecode(self.title)
        reg = re.compile(r'^(?:\([^\(\)]+\) )?(?:[^a-zA-Z0-9]+)?(.*)')

        return reg.match(title).group(1)[0]

def create_sortname(title):
    sortname = unidecode(title)
    reg = re.compile(r'^(\([^\(\)]+\))?(?: )?(.*)')
    matches = reg.match(sortname)
    if matches.group(1) is None:
        sortname = matches.group(2).lower()
    else:
        sortname = ('%s %s' % (matches.group(2), matches.group(1))).lower()
    sortname = re.sub(r'[^a-z0-9 ]', '', sortname)
    sortname = sortname.strip()
    return sortname

class SongAlias(db.Model):
    __tablename__ = 'songaliases'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    title = db.Column(db.Text, nullable=False)
    sort = db.Column(db.Text, nullable=False)
    title_id = db.Column(db.Integer, db.ForeignKey('songs.id'))
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'))

    def __init__(self, title, artist, *args, **kwargs):
        self.title = title
        self.sort = create_sortname(title)

        artist_search = Artist.query.filter_by(name=artist).first()

        if artist_search is not None:
            self.artist = artist_search
        else:
            self.artist = Artist(name=artist)

        super(SongAlias, self).__init__(*args, **kwargs)


    def __repr__(self):
        return '<Song alias "%s">' % (self.title, )

class SongFile(db.Model):
    __tablename__ = 'songfiles'

    id = db.Column(db.Integer, primary_key=True, nullable=False)
    path = db.Column(db.Text, nullable=False)
    filename = db.Column(db.Text, nullable=False)
    source = db.Column(db.Text)
    title_id = db.Column(db.Integer, db.ForeignKey('songs.id'))
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'))

    def __init__(self, path, filename, title, artist, source="", *args, **kwargs):
        self.path = path
        self.filename = filename

        if source is not "":
            self.source = source

        song_search = Song.query.filter_by(title=title).first()

        if song_search is not None:
            song_search.files.append(self)
        else:
            song = Song(title=title, sort=create_sortname(title))
            song.files.append(self)

        artist_search = Artist.query.filter_by(name=artist).first()

        if artist_search is not None:
            self.artist = artist_search
        else:
            self.artist = Artist(name=artist)

        super(SongFile, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Song file "%s">' % (self.filename, )

    @hybrid_property
    def title(self):
        return self.song.title

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
