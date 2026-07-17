import 'package:dartz/dartz.dart';

import '../../../../core/error/exceptions.dart';
import '../../../../core/error/failures.dart';
import '../../../../core/storage/token_storage.dart';
import '../../domain/entities/user.dart';
import '../../domain/repositories/auth_repository.dart';
import '../datasources/auth_remote_data_source.dart';
import '../models/auth_response_model.dart';

/// Concrete [AuthRepository] wiring the remote data source to secure token
/// storage and mapping exceptions to [Failure]s.
class AuthRepositoryImpl implements AuthRepository {
  AuthRepositoryImpl({
    required AuthRemoteDataSource remote,
    required TokenStorage tokenStorage,
  })  : _remote = remote,
        _tokens = tokenStorage;

  final AuthRemoteDataSource _remote;
  final TokenStorage _tokens;

  @override
  Future<Either<Failure, User>> register({
    required String email,
    required String password,
    String? fullName,
  }) =>
      _persistAndReturn(
        () => _remote.register(
          email: email,
          password: password,
          fullName: fullName,
        ),
      );

  @override
  Future<Either<Failure, User>> login({
    required String email,
    required String password,
  }) =>
      _persistAndReturn(
        () => _remote.login(email: email, password: password),
      );

  @override
  Future<Either<Failure, Unit>> logout() async {
    try {
      final refresh = await _tokens.readRefreshToken();
      if (refresh != null) {
        await _remote.logout(refresh);
      }
    } on Exception {
      // Even if the server call fails, we still clear local tokens below.
    }
    await _tokens.clear();
    return const Right(unit);
  }

  @override
  Future<Either<Failure, User>> currentUser() async {
    try {
      final user = await _remote.me();
      return Right(user);
    } on Exception catch (e) {
      return Left(_mapException(e));
    }
  }

  @override
  Future<bool> hasSession() => _tokens.hasSession();

  Future<Either<Failure, User>> _persistAndReturn(
    Future<AuthResponseModel> Function() call,
  ) async {
    try {
      final result = await call();
      await _tokens.saveTokens(
        accessToken: result.accessToken,
        refreshToken: result.refreshToken,
      );
      return Right(result.user);
    } on Exception catch (e) {
      return Left(_mapException(e));
    }
  }

  Failure _mapException(Exception e) {
    if (e is NetworkException) return NetworkFailure(e.message);
    if (e is UnauthorizedException) return AuthFailure(e.message);
    if (e is ServerException) {
      if (e.statusCode == 401 || e.statusCode == 403) {
        return AuthFailure(e.message);
      }
      if (e.statusCode == 422) return ValidationFailure(e.message);
      return ServerFailure(e.message, errorCode: e.errorCode);
    }
    return const UnexpectedFailure();
  }
}
