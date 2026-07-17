import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Encrypted, hardware-backed storage for auth tokens.
///
/// On Android this uses the Keystore-backed `EncryptedSharedPreferences`,
/// keeping tokens out of plaintext prefs and inaccessible to other apps.
class TokenStorage {
  TokenStorage([FlutterSecureStorage? storage])
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
            );

  final FlutterSecureStorage _storage;

  static const _kAccess = 'krishna.access_token';
  static const _kRefresh = 'krishna.refresh_token';

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _storage.write(key: _kAccess, value: accessToken);
    await _storage.write(key: _kRefresh, value: refreshToken);
  }

  Future<String?> readAccessToken() => _storage.read(key: _kAccess);

  Future<String?> readRefreshToken() => _storage.read(key: _kRefresh);

  Future<void> updateAccessToken(String accessToken) =>
      _storage.write(key: _kAccess, value: accessToken);

  Future<bool> hasSession() async =>
      (await _storage.read(key: _kRefresh)) != null;

  Future<void> clear() async {
    await _storage.delete(key: _kAccess);
    await _storage.delete(key: _kRefresh);
  }
}
