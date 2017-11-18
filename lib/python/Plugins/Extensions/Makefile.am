installdir = $(pkglibdir)/python/Plugins/Extensions

SUBDIRS = TuxboxPlugins CutListEditor CustomSubservices PicturePlayer MediaScanner MediaPlayer SocketMMI DVDBurn Modem Infopanel MenuSort MediaPortal mpgz

if HAVE_LIBDDVD
SUBDIRS += DVDPlayer
endif

if VUSOLO4K
SUBDIRS += MiniTV
endif

install_PYTHON = __init__.py
