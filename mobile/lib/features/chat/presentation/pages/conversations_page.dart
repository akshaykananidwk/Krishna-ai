import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/router/app_router.dart';
import '../providers/conversations_controller.dart';

/// Lists the user's conversations and lets them start a new one.
class ConversationsPage extends ConsumerWidget {
  const ConversationsPage({super.key});

  Future<void> _startNew(BuildContext context, WidgetRef ref) async {
    final conversation =
        await ref.read(conversationsControllerProvider.notifier).create();
    if (conversation != null && context.mounted) {
      context.push('${Routes.chat}/${conversation.id}');
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(conversationsControllerProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Chats')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _startNew(context, ref),
        icon: const Icon(Icons.add),
        label: const Text('New chat'),
      ),
      body: RefreshIndicator(
        onRefresh: () =>
            ref.read(conversationsControllerProvider.notifier).load(),
        child: state.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (err, _) => _ErrorView(
            message: '$err',
            onRetry: () =>
                ref.read(conversationsControllerProvider.notifier).load(),
          ),
          data: (conversations) {
            if (conversations.isEmpty) {
              return const _EmptyView();
            }
            return ListView.separated(
              itemCount: conversations.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, i) {
                final c = conversations[i];
                return Dismissible(
                  key: ValueKey(c.id),
                  direction: DismissDirection.endToStart,
                  background: Container(
                    color: Theme.of(context).colorScheme.errorContainer,
                    alignment: Alignment.centerRight,
                    padding: const EdgeInsets.only(right: 20),
                    child: const Icon(Icons.delete_outline),
                  ),
                  onDismissed: (_) => ref
                      .read(conversationsControllerProvider.notifier)
                      .delete(c.id),
                  child: ListTile(
                    leading: const CircleAvatar(child: Icon(Icons.forum_outlined)),
                    title: Text(
                      c.title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.push('${Routes.chat}/${c.id}'),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}

class _EmptyView extends StatelessWidget {
  const _EmptyView();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListView(
      children: [
        const SizedBox(height: 120),
        Icon(Icons.auto_awesome,
            size: 56, color: theme.colorScheme.primary),
        const SizedBox(height: 16),
        Center(
          child: Text('No conversations yet', style: theme.textTheme.titleMedium),
        ),
        const SizedBox(height: 8),
        Center(
          child: Text(
            'Tap “New chat” to talk with Krishna.',
            style: theme.textTheme.bodyMedium
                ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
        ),
      ],
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        const SizedBox(height: 120),
        const Center(child: Icon(Icons.error_outline, size: 48)),
        const SizedBox(height: 12),
        Center(child: Text(message, textAlign: TextAlign.center)),
        const SizedBox(height: 12),
        Center(
          child: FilledButton.tonal(onPressed: onRetry, child: const Text('Retry')),
        ),
      ],
    );
  }
}
