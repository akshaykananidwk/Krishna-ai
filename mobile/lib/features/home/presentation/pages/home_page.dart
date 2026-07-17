import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/router/app_router.dart';
import '../../../auth/presentation/providers/auth_controller.dart';

/// Placeholder authenticated landing screen. Later modules (AI Chat, Notes,
/// Tasks, ...) plug into this shell.
class HomePage extends ConsumerWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final state = ref.watch(authControllerProvider);
    final name = state is Authenticated ? state.user.displayName : '';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Krishna AI'),
        actions: [
          IconButton(
            tooltip: 'Sign out',
            icon: const Icon(Icons.logout),
            onPressed: () => ref.read(authControllerProvider.notifier).logout(),
          ),
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.auto_awesome,
                  size: 64, color: theme.colorScheme.primary),
              const SizedBox(height: 16),
              Text('Hello, $name', style: theme.textTheme.headlineSmall),
              const SizedBox(height: 8),
              Text(
                'Your assistant is ready. Start chatting with Krishna — more '
                'modules (Notes, Tasks, Voice) will appear here as they ship.',
                textAlign: TextAlign.center,
                style: theme.textTheme.bodyMedium
                    ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: () => context.push(Routes.conversations),
                icon: const Icon(Icons.chat_bubble_outline),
                label: const Text('Open AI Chat'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
