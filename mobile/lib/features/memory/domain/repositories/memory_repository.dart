import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/memory.dart';

/// Contract for the Memory Engine feature.
abstract interface class MemoryRepository {
  Future<Either<Failure, List<Memory>>> list({int limit, int offset});

  Future<Either<Failure, Memory>> create({
    required String content,
    String? title,
    String sourceType,
    List<String> tags,
  });

  Future<Either<Failure, List<MemorySearchHit>>> search({
    required String query,
    int topK,
  });

  Future<Either<Failure, Unit>> delete(String id);
}
