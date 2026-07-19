# Krishna AI — PHP + MySQL backend

A dependency-free PHP 8 backend (plain PDO, no Composer/framework) for shared
hosting such as **aaPanel + Apache + MariaDB 10.11 + PHP 8.3**. It serves the
REST API the Flutter app already expects.

> **Part 1 (this folder):** the web installer + **Auth API**
> (`register` / `login` / `refresh` / `logout` / `me`). The schema already
> creates every table (chat, memories, cache, audit) so the database is made
> once; the Chat (Part 2) and Memory (Part 3) route files plug in later.

## Where the files go

Upload the **contents of this folder** into your site's document root
(`/www/wwwroot/krishnaai.akdwk.in`). `config.php` is **not** included — the
installer writes it for you.

```
/www/wwwroot/krishnaai.akdwk.in/
├── .htaccess                 # protects config.php + schema.sql
├── schema.sql                # reference copy of all CREATE TABLEs
├── config.sample.php         # reference only (installer writes the real config.php)
├── install/
│   └── index.php             # web installer — visit /install once, then delete this folder
└── api/
    ├── .htaccess             # clean routing + passes the Authorization header
    ├── index.php             # front controller / router
    ├── lib/
    │   ├── .htaccess         # deny direct access
    │   ├── helpers.php        # json output, uuid, timestamps, validators
    │   ├── db.php             # PDO connection
    │   ├── jwt.php            # HS256 encode/verify
    │   └── auth.php           # tokens, rotation, current user, audit
    └── routes/
        ├── .htaccess         # deny direct access
        └── auth.php           # register / login / refresh / logout / me
```

## Install

1. In aaPanel, create a **MySQL database + user**.
2. Upload the files above to the document root.
3. Open **`https://krishnaai.akdwk.in/install`**, pass the environment checks,
   fill the form (DB creds + Google Gemini key + admin account), submit.
4. Delete the `install` folder.

The API is then live under `https://krishnaai.akdwk.in/api/...`. It accepts both
`/api/...` and `/api/v1/...` prefixes.

## Point the app at it

`mobile/lib/core/config/app_config.dart` — set the base URL to
`https://krishnaai.akdwk.in` and the prefix to `/api`.
