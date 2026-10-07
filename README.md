# Shopping Cart System

A personal learning project: an e-commerce web app built with Laravel 11 and PHP 8.2.
It has a customer storefront, an admin panel, user accounts and a small invoicing module.
I built it to learn how a real online store fits together, from routing and authentication
to the database and deployment with Docker.

## What I worked on

- **Store setup on Laravel 11**: set up a Laravel app with an open-source e-commerce
  package that provides the catalog, basket and checkout, and configured it for this project.
- **Invoicing module** (`myshop/`): an `Invoice` model with auto-generated invoice numbers,
  plus migrations for amount, customer and status.
- **Authentication**: registration, login, email verification and password reset.
- **Configurable routing**: optional multi-language, multi-vendor and top-level URL
  routing, switched on and off through `.env` settings.
- **Docker setup**: a Dockerfile (PHP 8.2 + Apache) and a Docker Compose stack with
  MySQL, MinIO for file storage and Mailpit for testing emails.
- **Cleanup and fixes**: moved settings to Laravel's `config()` so they work with
  config caching, fixed route constraints and updated the dependencies for Laravel 11.

## Tech stack

| Area | Tools |
|---|---|
| Backend | PHP 8.2, Laravel 11 |
| Frontend | Blade, Tailwind CSS, Alpine.js, Vite |
| Database | MySQL |
| DevOps | Docker, Docker Compose |
| Testing | PHPUnit |

## Project structure

| Folder | What it is |
|---|---|
| `/` (root) | The main shop application |
| `myshop/` | A separate Laravel 11 app where I built the invoicing module |
| `shopping_cart/` | A fresh Laravel 11 starter I used for experiments |

## Running it locally

You need PHP 8.2+, [Composer](https://getcomposer.org) 2.2+, Node.js and MySQL.

```
git clone https://github.com/Shivasaireddy007/shopping_cart_system.git
cd shopping_cart_system
composer install
npm install && npm run build
```

Create the `.env` file and add your database settings:

```
cp .env.example .env
php artisan key:generate
php artisan migrate
```

Load the demo shop data and create an admin account:

```
php artisan aimeos:setup --option=setup/default/demo:1
php artisan aimeos:account --super --admin you@example.com
```

Start the development server:

```
php artisan serve
```

- Storefront: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Admin panel: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

## Running with Docker

After `composer install`, start the full stack (app, MySQL, MinIO and Mailpit) with
Laravel Sail:

```
./vendor/bin/sail up -d
```

Emails sent by the app can be viewed in Mailpit at [http://localhost:8025](http://localhost:8025).

## Optional settings

These `.env` options turn on extra routing features:

| Setting | Effect |
|---|---|
| `SHOP_MULTILOCALE=true` | Adds the language to URLs, e.g. `/en/shop` |
| `SHOP_MULTISHOP=true` | Lets one installation host several vendor shops |
| `SHOP_MULTIROUTE=true` | Serves product and category pages from top-level URLs like `/shoes` |
| `SHOP_REGISTRATION=true` | Lets vendors sign up for their own shop |
| `SHOP_PERMISSION=editor` | Gives new vendors editor rights instead of admin |

## What I learned

- How the parts of a Laravel app fit together: routing, middleware, Eloquent models and migrations
- Why settings should be read through `config()` rather than `env()` once config is cached
- Writing database migrations that change existing tables safely
- Containerising a PHP app with Docker and Docker Compose
