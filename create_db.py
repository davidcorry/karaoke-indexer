from karaokeindex import db, app, SongFile, SongAlias
from icu import Locale, Collator
import os
import re
from unidecode import unidecode

# Requires PyObjC-Cocoa to be installed.
try:
    from AppKit import NSWorkspace
    from Foundation import *

    def is_alias (path):
        uti, err = NSWorkspace.sharedWorkspace().typeOfFile_error_(
            os.path.realpath(path), None)
        if err:
            raise Exception(unicode(err))
        else:
            return "com.apple.alias-file" == uti

    def target_of_alias(path):
        url = NSURL.fileURLWithPath_(path)
        bookmarkData, error = NSURL.bookmarkDataWithContentsOfURL_error_(url, None)
        if bookmarkData is None:
            return None
        opts = NSURLBookmarkResolutionWithoutUI | NSURLBookmarkResolutionWithoutMounting
        resolved, stale, error = NSURL.URLByResolvingBookmarkData_options_relativeToURL_bookmarkDataIsStale_error_(bookmarkData, opts, None, None, None)
        return resolved.path()
except:
    def is_alias (path):
        return False

def decolonize(str):
    str = re.sub(r' : ', ' / ', str)
    str = re.sub(r'([^ ]):([^ ])', '\\1/\\2', str)

    return str

def init():
    # try:
    #     os.remove(app.config['SQLALCHEMY_DATABASE_URI'][10:])
    # except:  # pragma: no cover
    #     pass
    # db.create_all()

    db.reflect()
    db.drop_all()
    db.create_all()

    root_dir = app.config['KARAOKE_DIR']

    collator = Collator.createInstance(Locale('en_US'))

    # artist_dirs = sorted(os.listdir(root_dir), key=collator.getSortKey)
    artist_dirs = os.listdir(root_dir)

    for artist in artist_dirs:
        if artist == '.DS_Store' or os.path.islink('%s/%s' % (root_dir, artist)):
            continue


        name = re.sub(r' : ', ' / ', artist)

        # song_dirs = sorted(os.listdir('%s/%s' % (root_dir, dirname)), key=collator.getSortKey)
        song_dirs = os.listdir('%s/%s' % (root_dir, artist))

        for title in song_dirs:
            title_dir = '%s/%s/%s' % (root_dir, artist, title)

            if title == '.DS_Store' or os.path.islink(title_dir):
                continue

            if is_alias(title_dir):
                print("a", end="", flush=True)
                song = decolonize(os.path.basename(target_of_alias(title_dir)))
                alias = SongAlias(title=title, artist=artist, song=song)
                db.session.add(alias)
                continue

            title = decolonize(title)

            song_files = [x for x in os.listdir(title_dir) if x.endswith(".mp3") or x.endswith(".mpg")]

            for file in song_files:
                print(".", end="", flush=True)
                songfile = SongFile(path=title_dir, filename=file, title=title, artist=artist)
                db.session.add(songfile)

    db.session.commit()

if __name__ == '__main__':
    init()
