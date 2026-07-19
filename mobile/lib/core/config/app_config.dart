/// Compile-time configuration.
///
/// Production is the DEFAULT, so `flutter build apk --release` needs no flags.
/// For local development against your own machine, override at build/run time:
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000 \
///               --dart-define=API_PREFIX=/api/v1
class AppConfig {
  const AppConfig._();

  /// Base URL of the Krishna AI backend (the live PHP backend by default).
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://krishnaai.akdwk.in',
  );

  /// Path prefix in front of every route. The PHP backend serves `/api/...`
  /// (and also accepts `/api/v1/...`).
  static const String apiPrefix = String.fromEnvironment(
    'API_PREFIX',
    defaultValue: '/api',
  );

  static const Duration connectTimeout = Duration(seconds: 15);
  static const Duration receiveTimeout = Duration(seconds: 30);
}
