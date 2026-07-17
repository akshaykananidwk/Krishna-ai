import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/user.dart';

/// Contract for authentication operations. The presentation layer depends on
/// this abstraction, never on a concrete implementation (Dependency Inversion).
abstract interface class AuthRepository {
  Future<Either<Failure, User>> register({
    required String email,
    required String password,
    String? fullName,
  });

  Future<Either<Failure, User>> login({
    required String email,
    required String password,
  });

  Future<Either<Failure, Unit>> logout();

  /// Returns the current user if a valid session exists, else a [Failure].
  Future<Either<Failure, User>> currentUser();

  Future<bool> hasSession();
}
