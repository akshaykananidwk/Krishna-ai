import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/di/providers.dart';
import '../data/memory_repository_impl.dart';
import '../domain/entities/memory.dart';
import '../domain/repositories/memory_repository.dart';

final memoryRepositoryProvider = Provider<MemoryRepository>((ref) {
  return MemoryRepositoryImpl(ref.watch(dioProvider));
});

/// Runs a semantic search; `AsyncValue` drives loading/error/data in the UI.
class MemorySearchController
    extends StateNotifier<AsyncValue<List<MemorySearchHit>>> {
  MemorySearchController(this._ref) : super(const AsyncValue.data([]));

  final Ref _ref;

  Future<void> search(String query) async {
    if (query.trim().isEmpty) {
      state = const AsyncValue.data([]);
      return;
    }
    state = const AsyncValue.loading();
    final result =
        await _ref.read(memoryRepositoryProvider).search(query: query.trim());
    state = result.fold(
      (failure) => AsyncValue.error(failure.message, StackTrace.current),
      AsyncValue.data,
    );
  }
}

final memorySearchControllerProvider = StateNotifierProvider.autoDispose<
    MemorySearchController, AsyncValue<List<MemorySearchHit>>>(
  MemorySearchController.new,
);
