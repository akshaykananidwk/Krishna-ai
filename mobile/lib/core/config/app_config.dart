/// Compile-time configuration.
///
/// Override at build time with:
///   flutter run --dart-define=API_BASE_URL=https://api.krishna.example.com
class AppConfig {
  const AppConfig._();

  /// Base URL of the Krishna AI backend. Defaults to the Android emulator
  /// loopback host (`10.0.2.2`) which maps to the developer machine.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  static const String apiPrefix = '/api/v1';

  static const Duration connectTimeout = Duration(seconds: 15);
  static const Duration receiveTimeout = Duration(seconds: 30);
}
