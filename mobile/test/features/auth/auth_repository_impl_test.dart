import 'package:dartz/dartz.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:krishna_ai/core/error/exceptions.dart';
import 'package:krishna_ai/core/error/failures.dart';
import 'package:krishna_ai/core/storage/token_storage.dart';
import 'package:krishna_ai/features/auth/data/datasources/auth_remote_data_source.dart';
import 'package:krishna_ai/features/auth/data/models/auth_response_model.dart';
import 'package:krishna_ai/features/auth/data/models/user_model.dart';
import 'package:krishna_ai/features/auth/data/repositories/auth_repository_impl.dart';
import 'package:mocktail/mocktail.dart';

class _MockRemote extends Mock implements AuthRemoteDataSource {}

class _MockTokenStorage extends Mock implements TokenStorage {}

void main() {
  late _MockRemote remote;
  late _MockTokenStorage tokens;
  late AuthRepositoryImpl repository;

  const authResponse = AuthResponseModel(
    accessToken: 'access-jwt',
    refreshToken: 'refresh-jwt',
    user: UserModel(id: 'u1', email: 'arjuna@example.com', fullName: 'Arjuna'),
  );

  setUp(() {
    remote = _MockRemote();
    tokens = _MockTokenStorage();
    repository = AuthRepositoryImpl(remote: remote, tokenStorage: tokens);
    when(() => tokens.saveTokens(
          accessToken: any(named: 'accessToken'),
          refreshToken: any(named: 'refreshToken'),
        )).thenAnswer((_) async {});
    when(() => tokens.clear()).thenAnswer((_) async {});
  });

  group('login', () {
    test('persists tokens and returns the user on success', () async {
      when(() => remote.login(
            email: any(named: 'email'),
            password: any(named: 'password'),
          )).thenAnswer((_) async => authResponse);

      final result = await repository.login(
        email: 'arjuna@example.com',
        password: 'Dharma123',
      );

      expect(result.isRight(), isTrue);
      result.fold(
        (_) => fail('expected success'),
        (user) => expect(user.email, 'arjuna@example.com'),
      );
      verify(() => tokens.saveTokens(
            accessToken: 'access-jwt',
            refreshToken: 'refresh-jwt',
          )).called(1);
    });

    test('maps 401 to AuthFailure and does not persist tokens', () async {
      when(() => remote.login(
            email: any(named: 'email'),
            password: any(named: 'password'),
          )).thenThrow(
        const ServerException('Invalid credentials',
            statusCode: 401, errorCode: 'invalid_credentials'),
      );

      final result = await repository.login(
        email: 'arjuna@example.com',
        password: 'wrong',
      );

      expect(result, isA<Left<Failure, dynamic>>());
      result.fold(
        (failure) => expect(failure, isA<AuthFailure>()),
        (_) => fail('expected failure'),
      );
      verifyNever(() => tokens.saveTokens(
            accessToken: any(named: 'accessToken'),
            refreshToken: any(named: 'refreshToken'),
          ));
    });

    test('maps a timeout to NetworkFailure', () async {
      when(() => remote.login(
            email: any(named: 'email'),
            password: any(named: 'password'),
          )).thenThrow(const NetworkException());

      final result = await repository.login(email: 'a@b.com', password: 'x');

      result.fold(
        (failure) => expect(failure, isA<NetworkFailure>()),
        (_) => fail('expected failure'),
      );
    });
  });

  group('logout', () {
    test('clears local tokens even when the server call throws', () async {
      when(() => tokens.readRefreshToken())
          .thenAnswer((_) async => 'refresh-jwt');
      when(() => remote.logout(any()))
          .thenThrow(const NetworkException());

      final result = await repository.logout();

      expect(result.isRight(), isTrue);
      verify(() => tokens.clear()).called(1);
    });
  });
}
