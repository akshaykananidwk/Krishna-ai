import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/pages/login_page.dart';
import '../../features/auth/presentation/pages/register_page.dart';
import '../../features/auth/presentation/pages/splash_page.dart';
import '../../features/auth/presentation/providers/auth_controller.dart';
import '../../features/chat/presentation/pages/chat_page.dart';
import '../../features/chat/presentation/pages/conversations_page.dart';
import '../../features/home/presentation/pages/home_page.dart';

/// Route paths as constants to avoid stringly-typed navigation.
abstract final class Routes {
  static const splash = '/splash';
  static const login = '/login';
  static const register = '/register';
  static const home = '/home';
  static const conversations = '/conversations';
  static const chat = '/chat';
}

/// A [GoRouter] whose redirects are driven by [AuthState]. A [ValueNotifier]
/// bridges the Riverpod notifier to go_router's [refreshListenable].
final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<AuthState>(const AuthInitial());
  ref.onDispose(refresh.dispose);
  ref.listen<AuthState>(
    authControllerProvider,
    (_, next) => refresh.value = next,
    fireImmediately: true,
  );

  return GoRouter(
    initialLocation: Routes.splash,
    refreshListenable: refresh,
    routes: [
      GoRoute(path: Routes.splash, builder: (_, __) => const SplashPage()),
      GoRoute(path: Routes.login, builder: (_, __) => const LoginPage()),
      GoRoute(path: Routes.register, builder: (_, __) => const RegisterPage()),
      GoRoute(path: Routes.home, builder: (_, __) => const HomePage()),
      GoRoute(
        path: Routes.conversations,
        builder: (_, __) => const ConversationsPage(),
      ),
      GoRoute(
        path: '${Routes.chat}/:id',
        builder: (_, state) =>
            ChatPage(conversationId: state.pathParameters['id']!),
      ),
    ],
    redirect: (context, state) {
      final auth = ref.read(authControllerProvider);
      final loc = state.matchedLocation;
      final onSplash = loc == Routes.splash;
      final onAuthPage = loc == Routes.login || loc == Routes.register;

      switch (auth) {
        case AuthInitial():
          // Cold start, before session restore begins.
          return onSplash ? null : Routes.splash;
        case AuthLoading():
          // In-flight login/register/bootstrap: stay put so button-level
          // spinners and error snackbars remain visible.
          return null;
        case Unauthenticated():
          return onAuthPage ? null : Routes.login;
        case Authenticated():
          return (onSplash || onAuthPage) ? Routes.home : null;
      }
    },
  );
});
