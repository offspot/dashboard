FROM alpine:3.19
LABEL org.opencontainers.image.source https://github.com/offspot/dashboard

RUN \
    apk add --no-cache curl dumb-init yaml python3 lighttpd \
    # FontAwesome font
    && curl -L -O https://use.fontawesome.com/releases/v6.5.1/fontawesome-free-6.5.1-web.zip \
        && unzip -o fontawesome-free-6.5.1-web.zip \
            fontawesome-free-6.5.1-web/css/* \
            fontawesome-free-6.5.1-web/webfonts/* \
            -d /var/www/assets/ \
        && mv /var/www/assets/fontawesome-free-6.5.1-web /var/www/assets/fontawesome \
        && rm -f fontawesome-free-6.5.1-web.zip \
    # python dependencies
    && python3 -m venv /usr/local/bin/gen-home_env \
    && /usr/local/bin/gen-home_env/bin/pip3 install --no-cache-dir -U pip \
    && /usr/local/bin/gen-home_env/bin/pip3 install \
        --no-cache-dir \
        Jinja2==3.1.2 PyYAML==6.0.1 humanfriendly==10.0 libzim==3.4.0 pycountry==23.12.11 \
    # install tailwind CSS cli
    && curl -L -o /usr/local/bin/tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/download/v3.4.3/tailwindcss-linux-arm64 \
    && chmod +x /usr/local/bin/tailwindcss \
    && apk del curl

ENV FQDN "generic.hotspot"
ENV NAME "My Hotspot"
# path in which to find code (templates)
ENV SRC_DIR "/src"
# path to packages YAML file
ENV PACKAGES_PATH "/src/home.yaml"
# path to write home HTML and assets file
ENV DEST_DIR "/var/www"
# folder storing ZIM files. unless DONT_UPDATE_PACKAGES, ZimPackages not in the folder
# will be removed (disabled) from packages.yaml
# discovered ZIM (not in YAML) will be added
ENV ZIM_DIR "/data/zims"
# set to skip packages.yaml update on start (reading ZIM_PATH folder)
ENV DONT_UPDATE_PACKAGES ""

# templates to write ZIM Package links to reader and ZIM downloads.
# Available patterns (to be replaced): `{fqdn}`, `{zim_name}`, `{zim_filename}`
ENV KIWIX_READER_LINK_TPL "//kiwix.{fqdn}/viewer#{zim_name}"
ENV KIWIX_DOWNLOAD_LINK_TPL "//zim-download.{fqdn}/{zim_filename}"

# WARN: this break apk but saves a lot of space
# it's OK on prod but comment it during dev if you need packages
RUN apk del apk-tools ca-certificates-bundle

COPY gen-home.py refresh-zims.py tailwind.config.js /src/
COPY templates /src/templates
COPY branding /var/www/branding
COPY assets /var/www/assets
COPY fallback.html /var/www/fallback.html
COPY home.yaml /src/
COPY lighttpd.conf /etc/lighttpd/
COPY entrypoint.sh /usr/local/bin/
COPY blocked /var/www/blocked/

WORKDIR /src

RUN \
    # gen final CSS
    tailwindcss -i /var/www/assets/dashboard-tailwind-src.css -o /var/www/assets/dashboard.css -c /src/tailwind.config.js \
    && rm -f /var/www/assets/dashboard-tailwind-src.css \
    && rm -f /usr/local/bin/tailwindcss \
    # store python bytecode in image
    && /usr/local/bin/gen-home_env/bin/python3 -m compileall /src/gen-home.py /src/refresh-zims.py && mv /src/__pycache__/*.pyc /usr/local/bin/gen-home_env/lib/

WORKDIR /var/www

HEALTHCHECK --interval=10s --timeout=2s CMD ["/bin/ls", "/tmp/.ready"]
ENTRYPOINT ["/usr/bin/dumb-init", "--", "/usr/local/bin/entrypoint.sh"]
CMD ["lighttpd", "-D", "-f", "/etc/lighttpd/lighttpd.conf"]

