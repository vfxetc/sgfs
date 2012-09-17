ENTRYPOINTS_BUILD := $(shell python -c 'import entrypoints.build; print entrypoints.build.__file__')

.PHONY : default entrypoints clean

default : entrypoints

ENTRYPOINTS_SENTINEL := bin/.make-sentinel
entrypoints : $(ENTRYPOINTS_SENTINEL)
$(ENTRYPOINTS_SENTINEL) : entrypoints.yml $(ENTRYPOINTS_BUILD)
	mkdir -p bin
	python -m entrypoints.build entrypoints.yml bin
	@ touch $(ENTRYPOINTS_SENTINEL)

clean :
	- rm -rf bin

