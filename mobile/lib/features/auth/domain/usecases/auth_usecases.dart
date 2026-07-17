import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/user.dart';
import '../repositories/auth_repository.dart';

/// Thin, single-responsibility use cases. They keep business intent explicit
/// and give the presentation layer a stable, mockable surface.

class LoginUseCase {
  const LoginUseCase(this._repository);
  final AuthRepository _repository;

  Future<Either<Failure, User>> call({
    required String email,
    required String password,
  }) =>
      _repository.login(email: email, password: password);
}

class RegisterUseCase {
  const RegisterUseCase(this._repository);
  final AuthRepository _repository;

  Future<Either<Failure, User>> call({
    required String email,
    required String password,
    String? fullName,
  }) =>
      _repository.register(
        email: email,
        password: password,
        fullName: fullName,
      );
}

class LogoutUseCase {
  const LogoutUseCase(this._repository);
  final AuthRepository _repository;

  Future<Either<Failure, Unit>> call() => _repository.logout();
}

class GetCurrentUserUseCase {
  const GetCurrentUserUseCase(this._repository);
  final AuthRepository _repository;

  Future<Either<Failure, User>> call() => _repository.currentUser();
}
