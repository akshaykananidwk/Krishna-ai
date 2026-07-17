import 'package:dio/dio.dart';

import '../config/app_config.dart';
import '../storage/token_storage.dart';
import 'auth_interceptor.dart';

/// Builds a configured [Dio] instance with base URL, timeouts and the auth
/// interceptor (which injects the bearer token and transparently refreshes it).
Dio buildDioClient({
  required TokenStorage tokenStorage,
  Dio? inner,
}) {
  final dio = inner ??
      Dio(
        BaseOptions(
          baseUrl: '${AppConfig.apiBaseUrl}${AppConfig.apiPrefix}',
          connectTimeout: AppConfig.connectTimeout,
          receiveTimeout: AppConfig.receiveTimeout,
          contentType: 'application/json',
          // Let us inspect non-2xx bodies instead of throwing on them.
          validateStatus: (status) => status != null && status < 500,
        ),
      );

  // A separate bare client for the refresh call avoids interceptor recursion.
  final refreshClient = Dio(
    BaseOptions(
      baseUrl: '${AppConfig.apiBaseUrl}${AppConfig.apiPrefix}',
      connectTimeout: AppConfig.connectTimeout,
      receiveTimeout: AppConfig.receiveTimeout,
      contentType: 'application/json',
    ),
  );

  dio.interceptors.add(
    AuthInterceptor(
      tokenStorage: tokenStorage,
      refreshClient: refreshClient,
      retryClient: dio,
    ),
  );
  return dio;
}
