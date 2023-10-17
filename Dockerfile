FROM postgres:latest

VOLUME /var/lib/postgresql/data

ENV POSTGRES_DB="football_networks"

EXPOSE 5432

CMD ["postgres"]