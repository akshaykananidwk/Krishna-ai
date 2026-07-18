import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/entities/memory.dart';
import 'memory_providers.dart';

/// Semantic search over the user's personal memory.
class MemorySearchPage extends ConsumerStatefulWidget {
  const MemorySearchPage({super.key});

  @override
  ConsumerState<MemorySearchPage> createState() => _MemorySearchPageState();
}

class _MemorySearchPageState extends ConsumerState<MemorySearchPage> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _search() =>
      ref.read(memorySearchControllerProvider.notifier).search(_controller.text);

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(memorySearchControllerProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Search Memory')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _controller,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _search(),
              decoration: InputDecoration(
                hintText: 'Ask your memory anything…',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.arrow_forward),
                  onPressed: _search,
                ),
              ),
            ),
          ),
          Expanded(
            child: state.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, _) => Center(child: Text('$err')),
              data: (hits) => hits.isEmpty
                  ? const _Empty()
                  : ListView.separated(
                      itemCount: hits.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, i) => _HitTile(hit: hits[i]),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

class _HitTile extends StatelessWidget {
  const _HitTile({required this.hit});
  final MemorySearchHit hit;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final m = hit.memory;
    return ListTile(
      title: Text(
        m.title ?? m.content,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Text(
        m.content,
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
      ),
      trailing: Chip(
        label: Text('${(hit.similarity * 100).round()}%'),
        visualDensity: VisualDensity.compact,
        backgroundColor: theme.colorScheme.secondaryContainer,
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.travel_explore,
                size: 48, color: theme.colorScheme.primary),
            const SizedBox(height: 12),
            Text('Search your personal knowledge',
                style: theme.textTheme.titleMedium),
          ],
        ),
      ),
    );
  }
}
