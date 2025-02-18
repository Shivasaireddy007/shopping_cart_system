
## Features

Shopping Cart is a full-featured e-commerce package:

* JSON REST API based on jsonapi.org
* GraphQL API for administration
* Perfect fit for AWS, Google, Azure and Kubernetes based clouds
* Multi vendor, multi channel and multi warehouse
* From one to 1,000,000,000+ items
* For multi-tentant e-commerce SaaS solutions with unlimited vendors
* Bundles, vouchers, virtual, configurable, custom and event products
* Subscriptions with recurring payments
* 100+ payment gateways
* Full RTL support (frontend and backend)
* Block/tier pricing out of the box
* Extension for customer/group based prices
* Discount and voucher support
* Flexible basket rule system
* Full-featured admin backend
* Beautiful admin dashboard
* Configurable product data sets
* Completly modular structure
* Optimized for smart phones and tablets
* High quality source code

... and more features...

![Image](https://github.com/user-attachments/assets/fe3dd9d4-528d-43d3-a8c2-3e00ebfd269a)

## Headless distribution

To build a single page application (SPA) respectively a progressive web
application (PWA), the headless distribution is the right choice
with API-only and JWT authentication pre-configured:


## Requirements

The shop distribution requires:
- Linux/Unix, WAMP/XAMP or MacOS environment
- PHP >= 8.2
- MySQL >= 5.7.8, MariaDB >= 10.2.2, PostgreSQL 9.6+, SQL Server 2019+
- Web server (Apache, Nginx or integrated PHP web server for testing)

If required PHP extensions are missing, `composer` will tell you about the missing
dependencies.

## Installation

To install the Aimeos shop application, you need [composer 2.2+](https://getcomposer.org).
On the CLI, execute this command for a complete installation including a working setup:

```
wget https://getcomposer.org/download/latest-stable/composer.phar -O composer
php composer create-project shopping_cart_system/shopping_cart_system_myshop
```

You will be asked for the parameters of your database and mail server as well as an
e-mail and password used for creating the administration account.

In a local environment, you can use the integrated PHP web server to test your new Aimeos
installation. Simply execute the following command to start the web server:

```
cd myshop
php artisan serve
```

## Frontend

After the installation, you can test the Aimeos shop frontend by calling the URL of your
VHost in your browser. If you use the integrated PHP web server, you should browse
this URL: [http://127.0.0.1:8000](http://127.0.0.1:8000)

![Image](https://github.com/user-attachments/assets/003d2661-3b21-4c8e-9d6a-0c60a4cd35d0)



## Backend

The shopping cart administration interface will be available at `/admin` in your VHost. When using
the integrated PHP web server, call this URL: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

![Image](https://github.com/user-attachments/assets/6b212ac1-ea64-4f29-b9a3-4c38dfc122c9)


## Multi-routing

If you want to have all category, product and page URLs as top level URLs like `/shoes`,
`/my-sneaker` and `/about-us`, then you can enable the Aimeos multi-routing feature in
your `./myshop/.env` file:

```
SHOP_MULTIROUTE=true
```

## Multi-vendor

To enable multi-vendor features, add this settings to the `./myshop/.env` file:

```
SHOP_MULTISHOP=true
```

If you want to allow vendors to register themselves as sellers, set this option in the
`./myshop/.env` file too:

```
SHOP_REGISTRATION=true
```

By default, newly registered sellers have administrator privileges in the backend for
their own site. For a more limited access to the backend, you can change the permission
level to "editor" in the `./myshop/.env` file:
