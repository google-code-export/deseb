<br /><br />

<h1><font color='red'>PROJECT HAS MOVED TO GITHUB!</font></h1>
Please click here: https://github.com/keredson/deseb

This repository is no longer supported.

<br /><br />

# Django External Schema Evolution Branch #

Django, via the command `./manage syncdb`, can automatically build a database schema based on your applications `models.py` file.  However, after you've done this once, it leaves you with two unpleasant follow-up options if you ever make any changes to your model structure:
  1. destroy your existing schema (along with all your data) and let `./manage syncdb` rebuild it for you
  1. manage your own schema upgrades by writing your own SQL

Project deseb aims to fill this void by providing s third option:
  1. generate schema upgrades via the command: `./manage evolvedb`

# Installation Instructions #

  1. cd into your project directory (where your `manage.py` is) or anywhere in your PYTHON\_PATH
  1. run: `svn checkout http://deseb.googlecode.com/svn/trunk/src/deseb`
  1. add `import deseb` to the top of `settings.py`

# Using deseb #

  1. make modifications to your `models.py` (either a new or existing project)
  1. run `./manage evolvedb`
  1. lather, rinse, repeat

Look at [usage](Usage.md) and a [sample run](SampleRun.md).

# Software requirements #
  * django-0.96.1 or latest django trunk or django-newforms-admin branch
  * Worked with mysql 5.0 and postgresql 8.2. Not tested with other versions of these backends.
  * May not work or work incorrectly with sqlite3.
  * Patches highly appreciated ;)

# Documentation #

  * [project status](Status.md)
  * [FAQ](FAQ.md)
  * [full documentation](Documentation.md)