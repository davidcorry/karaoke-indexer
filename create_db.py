from karaokeindex import db, app, Artist, Song
from icu import Locale, Collator
import os
import re
from unidecode import unidecode

def init():
    try:
        os.remove(app.config['SQLALCHEMY_DATABASE_URI'][10:])
    except:  # pragma: no cover
        pass
    db.create_all()

    root_dir = app.config['KARAOKE_DIR']

    collator = Collator.createInstance(Locale('en_US'))

    artist_dirs = sorted(os.listdir(root_dir), key=collator.getSortKey)

    for dirname in artist_dirs:
        if dirname == '.DS_Store':
            continue

        name = re.sub(r' : ', ' / ', dirname)

        artist = Artist(name=name)

        song_dirs = sorted(os.listdir('%s/%s' % (root_dir, dirname)), key=collator.getSortKey)

        for songdirname in song_dirs:
            if songdirname == '.DS_Store':
                continue

            title = re.sub(r' : ', ' / ', songdirname)
            title = re.sub(r'([^ ]):([^ ])', '\\1/\\2', songdirname)

            collision = Song.query.filter_by(title=title).first()

            if collision is not None:
                song = collision
            else:
                sortname = unidecode(songdirname)
                reg = re.compile(r'^(\([^\(\)]+\))?(?: )?(.*)')
                matches = reg.match(sortname)
                if matches.group(1) is None:
                    sortname = matches.group(2).lower()
                else:
                    sortname = ('%s %s' % (matches.group(2), matches.group(1))).lower()
                sortname = re.sub(r'[^a-z0-9 ]', '', sortname)
                sortname = sortname.strip()

                song = Song(title=title, sort=sortname)

            artist.songs.append(song)

        db.session.add(artist)

    db.session.commit()

if __name__ == '__main__':
    init()
