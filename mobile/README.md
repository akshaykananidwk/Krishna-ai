# Krishna AI — Mobile (Flutter)

The Android client for Krishna AI, built with **Flutter + Material 3** following
**Clean Architecture** (data / domain / presentation) and the **Repository
pattern**, with **Riverpod** for state management and dependency injection.

## Project layout

```
lib/
├── main.dart                 # entrypoint (ProviderScope)
├── app.dart                  # root widget → MaterialApp.router
├── core/                     # cross-cutting concerns
│   ├── config/               # compile-time config (API base URL, timeouts)
│   ├── di/                   # Riverpod providers (Dio, secure storage)
│   ├── error/                # exceptions + typed Failures
│   ├── network/              # Dio client + auth/refresh interceptor
│   ├── router/               # go_router with auth-aware redirects
│   ├── storage/              # Keystore-backed secure token storage
│   ├── theme/                # Material 3 light/dark themes
│   └── utils/                # validators
└── features/
    ├── auth/                 # Module 1 — Authentication
    │   ├── data/             #   models, remote data source, repo impl
    │   ├── domain/           #   entities, repo interface, use cases
    │   └── presentation/     #   providers, pages, widgets
    └── home/                 # authenticated landing shell
```

## Architecture at a glance

```
UI (pages/widgets)
      │  watches
      ▼
AuthController (StateNotifier)  ──uses──▶  Use cases  ──▶  AuthRepository (interface)
                                                                 ▲
                                                                 │ implements
                                          AuthRepositoryImpl ─────┘
                                             │            │
                               RemoteDataSource(Dio)   TokenStorage(secure)
```

Dependencies point **inwards**: `presentation → domain ← data`. The domain layer
knows nothing about Flutter, Dio, or storage.

## Getting started

Platform folders (`android/`, `ios/`) are generated, not committed. After
cloning, run once:

```bash
cd mobile
flutter create .            # generates android/ + ios/ scaffolding
flutter pub get
```

Run against a locally running backend (see `../backend`):

```bash
# Android emulator reaches the host at 10.0.2.2 (the default).
flutter run

# Or point at a deployed API:
flutter run --dart-define=API_BASE_URL=https://api.krishna.example.com
```

### Required Android permissions

Release APKs need the INTERNET permission (Flutter only adds it to debug
builds). The **Build APK** GitHub Actions workflow injects it automatically
after `flutter create .`. If you build locally, add it yourself to
`android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.INTERNET"/>
```

Later modules (Voice, Notifications) will add `RECORD_AUDIO` and
`POST_NOTIFICATIONS`.

## Testing

```bash
flutter test            # unit + widget tests
flutter test --coverage
flutter analyze         # static analysis
dart format .           # formatting
```

Current coverage: validators (unit), `AuthRepositoryImpl` (mocked), and the
login page (widget).
