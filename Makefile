VIRTUALENV=virtualenv

all:	migrate

migrate:
	@rm -f redirect.txt
	@( . ./${VIRTUALENV}/bin/activate && ./s9y-to-hugo.py --targetdir=newblog --webprefix="/" --oldwebprefix="/blog" --rewritefile=redirect.txt --rewritetype=apache2 --dbtype=pg --dbhost=127.0.0.1 --dbuser=pg --dbname=blog --dbprefix=serendipity --imagedir=. --remove-s9y-id --add-date-to-url --write-html --use-bundles --add-year-link-to-archive --archive-link="/all-posts/" -v )

migrate-server:
	@( . ./${VIRTUALENV}/bin/activate && cd newblog && hugo server --verbose --log --verboseLog )

virtualenv:	clean-virtualenv
	virtualenv --python=python3 ${VIRTUALENV}/
	( . ./${VIRTUALENV}/bin/activate && pip3 install -r requirements.txt )

clean-virtualenv:
	rm -rf ${VIRTUALENV}/

.PHONY: all virtualenv clean-virtualenv migrate migrate-server
