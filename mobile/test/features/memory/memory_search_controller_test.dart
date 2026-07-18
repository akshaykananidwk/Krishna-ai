import 'package:dartz/dartz.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:krishna_ai/core/error/failures.dart';
import 'package:krishna_ai/features/memory/domain/entities/memory.dart';
import 'package:krishna_ai/features/memory/domain/repositories/memory_repository.dart';
import 'package:krishna_ai/features/memory/presentation/memory_providers.dart';

class _FakeMemoryRepository implements MemoryRepository {
  _FakeMemoryRepository({this.fail = false});
  final bool fail;

  @override
  Future<Either<Failure, List<MemorySearchHit>>> search({
    required String query,
    int topK = 8,
  }) async {
    if (fail) return const Left(NetworkFailure());
    return Right([
      MemorySearchHit(
        memory: Memory(
          id: '1',
          sourceType: 'note',
          content: 'result for $query',
          pinned: false,
          createdAt: DateTime(2026),
        ),
        score: 0.9,
        similarity: 0.8,
      ),
    ]);
  }

  @override
  Future<Either<Failure, Memory>> create({
    required String content,
    String? title,
    String sourceType = 'note',
    List<String> tags = const [],
  }) =>
      throw UnimplementedError();
  @override
  Future<Either<Failure, Unit>> delete(String id) => throw UnimplementedError();
  @override
  Future<Either<Failure, List<Memory>>> list({int limit = 50, int offset = 0}) =>
      throw UnimplementedError();
}

Future<void> _settle() => Future<void>.delayed(const Duration(milliseconds: 10));

void main() {
  test('empty query yields empty results', () async {
    final container = ProviderContainer(
      overrides: [
        memoryRepositoryProvider.overrideWithValue(_FakeMemoryRepository()),
      ],
    );
    addTearDown(container.dispose);
    container.listen(memorySearchControllerProvider, (_, __) {});

    await container.read(memorySearchControllerProvider.notifier).search('   ');
    expect(container.read(memorySearchControllerProvider).value, isEmpty);
  });

  test('returns ranked hits on success', () async {
    final container = ProviderContainer(
      overrides: [
        memoryRepositoryProvider.overrideWithValue(_FakeMemoryRepository()),
      ],
    );
    addTearDown(container.dispose);
    container.listen(memorySearchControllerProvider, (_, __) {});

    await container.read(memorySearchControllerProvider.notifier).search('apollo');
    await _settle();

    final hits = container.read(memorySearchControllerProvider).value!;
    expect(hits, hasLength(1));
    expect(hits.first.memory.content, contains('apollo'));
  });

  test('surfaces a failure as an error state', () async {
    final container = ProviderContainer(
      overrides: [
        memoryRepositoryProvider
            .overrideWithValue(_FakeMemoryRepository(fail: true)),
      ],
    );
    addTearDown(container.dispose);
    container.listen(memorySearchControllerProvider, (_, __) {});

    await container.read(memorySearchControllerProvider.notifier).search('x');
    await _settle();

    expect(container.read(memorySearchControllerProvider).hasError, isTrue);
  });
}
