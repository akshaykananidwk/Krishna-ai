import 'package:dio/dio.dart';

import '../../../../core/error/exceptions.dart';
import '../models/auth_response_model.dart';
import '../models/user_model.dart';

/// Talks to the backend authentication endpoints. Translates transport-level
/// problems into typed [ServerException] / [NetworkException]s.
abstract interface class AuthRemoteDataSource {
  Future<AuthResponseModel> register({
    required String email,
    required String password,
    String? fullName,
  });

  Future<AuthResponseModel> login({
    required String email,
    required String password,
  });

  Future<UserModel> me();

  Future<void> logout(String refreshToken);
}

class AuthRemoteDataSourceImpl implements AuthRemoteDataSource {
  const AuthRemoteDataSourceImpl(this._dio);
  final Dio _dio;

  @override
  Future<AuthResponseModel> register({
    required String email,
    required String password,
    String? fullName,
  }) =>
      _authCall('/auth/register', {
        'email': email,
        'password': password,
        if (fullName != null && fullName.isNotEmpty) 'full_name': fullName,
      });

  @override
  Future<AuthResponseModel> login({
    required String email,
    required String password,
  }) =>
      _authCall('/auth/login', {'email': email, 'password': password});

  @override
  Future<UserModel> me() async {
    try {
      final resp = await _dio.get<Map<String, dynamic>>('/auth/me');
      _ensureSuccess(resp);
      return UserModel.fromJson(resp.data!);
    } on DioException catch (e) {
      throw _mapDioError(e);
    }
  }

  @override
  Future<void> logout(String refreshToken) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/auth/logout',
        data: {'refresh_token': refreshToken},
      );
    } on DioException catch (e) {
      throw _mapDioError(e);
    }
  }

  Future<AuthResponseModel> _authCall(
    String path,
    Map<String, dynamic> body,
  ) async {
    try {
      final resp = await _dio.post<Map<String, dynamic>>(path, data: body);
      _ensureSuccess(resp);
      return AuthResponseModel.fromJson(resp.data!);
    } on DioException catch (e) {
      throw _mapDioError(e);
    }
  }

  void _ensureSuccess(Response<Map<String, dynamic>> resp) {
    final code = resp.statusCode ?? 0;
    if (code >= 200 && code < 300) return;
    final data = resp.data ?? const {};
    throw ServerException(
      (data['detail'] as String?) ?? 'Request failed.',
      statusCode: code,
      errorCode: data['error_code'] as String?,
    );
  }

  Exception _mapDioError(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.connectionError:
        return const NetworkException();
      default:
        final data = e.response?.data;
        final detail = data is Map<String, dynamic>
            ? data['detail'] as String?
            : null;
        return ServerException(
          detail ?? e.message ?? 'Server error.',
          statusCode: e.response?.statusCode,
          errorCode: data is Map<String, dynamic>
              ? data['error_code'] as String?
              : null,
        );
    }
  }
}
