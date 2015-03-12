# Sample Run #1 #
(adding a field to an existing model)

Assume this is your manage.py:
```
from django.db import models

class Poll(models.Model):
    question = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    author = models.CharField(max_length=200)
    def __str__(self):
        return self.question
    
class Choice(models.Model):
    poll = models.ForeignKey(Poll)
    choice = models.CharField(max_length=200)
    votes = models.IntegerField()
    def __str__(self):
        return self.choice
```

And you add `creatorIp = models.IPAddressField()` to class `Poll`, and then run `./manage evolvedb`:

```
fingerprint for 'case01_add_field' is 'fv1:1116633177' (unrecognized)
case01_add_field: the following schema upgrade is available:

ALTER TABLE `case01_add_field_poll` ADD COLUMN `creatorIp` char(15) NOT NULL;

do you want to run the preceeding commands?
type 'yes' to continue, or 'no' to cancel: yes
schema upgrade executed

do you want to save these commands in case01_add_field.schema_evolution?
type 'yes' to continue, or 'no' to cancel: yes
```

Your schema has now been upgraded, and the following has been recorded to `case01_add_field/schema_evolution.py`:

```
mysql_evolutions = [
    [('fv1:1116633177','fv1:949078369'), # generated 2007-12-09 17:40:23.114770
        "ALTER TABLE `case01_add_field_poll` ADD COLUMN `creatorIp` char(15) NOT NULL;",
    ],
] # don't delete this comment! ## mysql_evolutions_end ##
```

Then you deploy your new code to production, again with `./manage evolvedb`:

```
case01_add_field.schema_evolution module found (2 fingerprints, 1 evolutions)
fingerprint for 'case01_add_field' is 'fv1:1116633177' (recognized)
         and a managed schema upgrade to 'fv1:949078369' is available:

ALTER TABLE `case01_add_field_poll` ADD COLUMN `creatorIp` char(15) NOT NULL;

do you want to run the preceeding commands?
type 'yes' to continue, or 'no' to cancel: yes
schema upgrade executed
        fingerprint verification successful

fingerprint for 'case01_add_field' is 'fv1:949078369' (recognized)
```

Note that for the production deployment database introspection is NOT used (except to identify and verify the schema fingerprints).  The schema upgrade code is the developer-verified code generated and saved during development.