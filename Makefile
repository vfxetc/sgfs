ENTRYPOINTS_BUILD := $(shell python -c 'import entrypoints.build as x; print x.__file__')
SGACTIONS_DEPLOY := $(shell python -c 'import sgactions.deploy as x; print x.__file__')

.PHONY : default entrypoints sgactions clean

default : entrypoints sgactions

ENTRYPOINTS_SENTINEL := bin/.make-sentinel
entrypoints : $(ENTRYPOINTS_SENTINEL)
$(ENTRYPOINTS_SENTINEL) : entrypoints.yml $(ENTRYPOINTS_BUILD)
	mkdir -p bin
	python -m entrypoints.build entrypoints.yml bin
	@ touch $(ENTRYPOINTS_SENTINEL)

SGACTIONS_SENTINEL := .sgactions.make-sentinel
entrypoints : $(SGACTIONS_SENTINEL)
$(SGACTIONS_SENTINEL) : sgactions.yml $(SGACTIONS_DEPLOY)
	python -m sgactions.deploy sgactions.yml
	@ touch $(SGACTIONS_SENTINEL)

clean :
	- rm -rf bin

