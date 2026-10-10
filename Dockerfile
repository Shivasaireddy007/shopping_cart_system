# Build frontend assets (public/build is not committed)
FROM node:20-alpine AS assets
WORKDIR /app
COPY package.json package-lock.json vite.config.js postcss.config.js tailwind.config.js ./
COPY resources ./resources
RUN npm ci && npm run build

# Use official PHP image with Apache
FROM php:8.3-apache

# Install required PHP extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libicu-dev \
    libzip-dev \
    unzip \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install gd intl opcache pdo pdo_mysql mysqli zip \
    && rm -rf /var/lib/apt/lists/*

# Production PHP settings with opcache
RUN cp "$PHP_INI_DIR/php.ini-production" "$PHP_INI_DIR/php.ini" \
    && printf 'opcache.enable=1\nopcache.validate_timestamps=0\nopcache.memory_consumption=128\nmemory_limit=256M\n' > "$PHP_INI_DIR/conf.d/zz-app.ini"

# Enable Apache mod_rewrite for Laravel
RUN a2enmod rewrite

# Serve the Laravel public/ directory instead of the project root
ENV APACHE_DOCUMENT_ROOT=/var/www/html/public
RUN sed -ri -e 's!/var/www/html!${APACHE_DOCUMENT_ROOT}!g' /etc/apache2/sites-available/*.conf \
    && sed -ri -e 's!/var/www/!${APACHE_DOCUMENT_ROOT}!g' /etc/apache2/apache2.conf /etc/apache2/conf-available/*.conf

# Set working directory
WORKDIR /var/www/html

# Install Composer
COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# Copy Laravel project files to container
COPY . /var/www/html/

# Add the built frontend assets
COPY --from=assets /app/public/build /var/www/html/public/build

# Install PHP dependencies (vendor/ is excluded by .dockerignore)
RUN composer install --no-dev --no-interaction --no-scripts --prefer-dist --optimize-autoloader \
    && php artisan package:discover --ansi \
    && php artisan vendor:publish --tag=public --force

# Set proper permissions
RUN chown -R www-data:www-data /var/www/html \
    && chmod -R 775 /var/www/html/storage /var/www/html/bootstrap/cache

# Expose port 80 (Apache)
EXPOSE 80

# Prepare the database and start Apache (see docker/entrypoint.sh)
COPY docker/entrypoint.sh /usr/local/bin/entrypoint
RUN chmod +x /usr/local/bin/entrypoint
CMD ["entrypoint"]
