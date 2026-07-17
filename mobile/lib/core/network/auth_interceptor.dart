import 'dart:async';

import 'package:dio/dio.dart';

import '../storage/token_storage.dart';

/// Injects the access token on every request and, on a 401, attempts a single
/// transparent refresh-and-retry using the stored refresh token.
///
/// Concurrent 401s share one in-flight refresh via [_refreshCompleter] so the
/// backend is not hammered with parallel refresh calls.
class AuthInterceptor extends Interceptor {
  AuthInterceptor({
    required TokenStorage tokenStorage,
    required Dio refreshClient,
    required Dio retryClient,
  })  : _tokens = tokenStorage,
        _refreshClient = refreshClient,
        _retryClient = retryClient;

  final TokenStorage _tokens;
  final Dio _refreshClient;
  final Dio _retryClient;

  Completer<String?>? _refreshCompleter;

  static const _noAuthPaths = {'/auth/login', '/auth/register', '/auth/refresh'};
  static const _retriedHeader = 'X-Krishna-Retried';

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    if (!_noAuthPaths.contains(options.path)) {
      final access = await _tokens.readAccessToken();
      if (access != null) {
        options.headers['Authorization'] = 'Bearer $access';
      }
    }
    handler.next(options);
  }

  @override
  Future<void> onResponse(
    Response response,
    ResponseInterceptorHandler handler,
  ) async {
    if (response.statusCode == 401 &&
        !_noAuthPaths.contains(response.requestOptions.path) &&
        // Guard against an infinite refresh loop: only retry once.
        response.requestOptions.headers[_retriedHeader] == null) {
      final newToken = await _refreshToken();
      if (newToken != null) {
        final retried = await _retry(response.requestOptions, newToken);
        return handler.resolve(retried);
      }
    }
    handler.next(response);
  }

  Future<String?> _refreshToken() {
    // Coalesce concurrent refreshes.
    if (_refreshCompleter != null) return _refreshCompleter!.future;

    final completer = Completer<String?>();
    _refreshCompleter = completer;

    unawaited(_doRefresh().then((token) {
      completer.complete(token);
      _refreshCompleter = null;
    }));

    return completer.future;
  }

  Future<String?> _doRefresh() async {
    final refresh = await _tokens.readRefreshToken();
    if (refresh == null) return null;
    try {
      final resp = await _refreshClient.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: {'refresh_token': refresh},
      );
      final data = resp.data;
      if (resp.statusCode == 200 && data != null) {
        final access = data['access_token'] as String;
        final newRefresh = data['refresh_token'] as String;
        await _tokens.saveTokens(accessToken: access, refreshToken: newRefresh);
        return access;
      }
    } on DioException {
      // fall through to clear
    }
    await _tokens.clear();
    return null;
  }

  Future<Response> _retry(RequestOptions options, String accessToken) {
    final headers = Map<String, dynamic>.from(options.headers)
      ..['Authorization'] = 'Bearer $accessToken'
      ..[_retriedHeader] = '1';
    return _retryClient.request(
      options.path,
      data: options.data,
      queryParameters: options.queryParameters,
      options: Options(method: options.method, headers: headers),
    );
  }
}
