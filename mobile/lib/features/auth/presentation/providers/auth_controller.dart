import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/user.dart';
import 'auth_providers.dart';

/// The authentication state exposed to the UI.
sealed class AuthState {
  const AuthState();
}

class AuthInitial extends AuthState {
  const AuthInitial();
}

class AuthLoading extends AuthState {
  const AuthLoading();
}

class Authenticated extends AuthState {
  const Authenticated(this.user);
  final User user;
}

class Unauthenticated extends AuthState {
  const Unauthenticated({this.message});
  final String? message;
}

/// Drives the auth flow: bootstrap from a stored session, login, register,
/// logout. The UI listens to this notifier and reacts to state transitions.
class AuthController extends StateNotifier<AuthState> {
  AuthController(this._ref) : super(const AuthInitial());

  final Ref _ref;

  /// Called on startup: if a refresh token exists, verify it against /me.
  Future<void> bootstrap() async {
    state = const AuthLoading();
    final repo = _ref.read(authRepositoryProvider);
    if (!await repo.hasSession()) {
      state = const Unauthenticated();
      return;
    }
    final result = await _ref.read(getCurrentUserUseCaseProvider)();
    result.fold(
      (_) => state = const Unauthenticated(),
      (user) => state = Authenticated(user),
    );
  }

  Future<void> login({required String email, required String password}) async {
    state = const AuthLoading();
    final result = await _ref.read(loginUseCaseProvider)(
      email: email,
      password: password,
    );
    result.fold(
      (failure) => state = Unauthenticated(message: failure.message),
      (user) => state = Authenticated(user),
    );
  }

  Future<void> register({
    required String email,
    required String password,
    String? fullName,
  }) async {
    state = const AuthLoading();
    final result = await _ref.read(registerUseCaseProvider)(
      email: email,
      password: password,
      fullName: fullName,
    );
    result.fold(
      (failure) => state = Unauthenticated(message: failure.message),
      (user) => state = Authenticated(user),
    );
  }

  Future<void> logout() async {
    await _ref.read(logoutUseCaseProvider)();
    state = const Unauthenticated();
  }
}

final authControllerProvider =
    StateNotifierProvider<AuthController, AuthState>((ref) {
  return AuthController(ref);
});
