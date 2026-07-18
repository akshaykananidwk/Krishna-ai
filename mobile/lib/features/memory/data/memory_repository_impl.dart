import 'package:dartz/dartz.dart';
import 'package:dio/dio.dart';

import '../../../core/error/exceptions.dart';
import '../../../core/error/failures.dart';
import '../domain/entities/memory.dart';
import '../domain/repositories/memory_repository.dart';
import 'memory_models.dart';

/// Talks to the Memory Engine endpoints (`/api/v1/memory`).
class MemoryRepositoryImpl implements MemoryRepository {
  const MemoryRepositoryImpl(this._dio);
  final Dio _dio;

  @override
  Future<Either<Failure, List<Memory>>> list({
    int limit = 50,
    int offset = 0,
  }) =>
      _guard(() async {
        final resp = await _dio.get<List<dynamic>>(
          '/memory',
          queryParameters: {'limit': limit, 'offset': offset},
        );
        _ensure(resp);
        return (resp.data ?? [])
            .map((e) => MemoryModel.fromJson(e as Map<String, dynamic>))
            .toList();
      });

  @override
  Future<Either<Failure, Memory>> create({
    required String content,
    String? title,
    String sourceType = 'note',
    List<String> tags = const [],
  }) =>
      _guard(() async {
        final resp = await _dio.post<Map<String, dynamic>>(
          '/memory',
          data: {
            'content': content,
            if (title != null) 'title': title,
            'source_type': sourceType,
            'tags': tags,
          },
        );
        _ensure(resp);
        return MemoryModel.fromJson(resp.data!);
      });

  @override
  Future<Either<Failure, List<MemorySearchHit>>> search({
    required String query,
    int topK = 8,
  }) =>
      _guard(() async {
        final resp = await _dio.post<Map<String, dynamic>>(
          '/memory/search',
          data: {'query': query, 'top_k': topK},
        );
        _ensure(resp);
        final results = resp.data!['results'] as List<dynamic>;
        return results
            .map((e) => MemorySearchHitModel.fromJson(e as Map<String, dynamic>))
            .toList();
      });

  @override
  Future<Either<Failure, Unit>> delete(String id) => _guard(() async {
        final resp = await _dio.delete<Map<String, dynamic>>('/memory/$id');
        _ensure(resp);
        return unit;
      });

  void _ensure(Response<dynamic> resp) {
    final code = resp.statusCode ?? 0;
    if (code >= 200 && code < 300) return;
    final data = resp.data;
    final detail = data is Map<String, dynamic> ? data['detail'] as String? : null;
    throw ServerException(detail ?? 'Request failed.', statusCode: code);
  }

  Future<Either<Failure, T>> _guard<T>(Future<T> Function() call) async {
    try {
      return Right(await call());
    } on ServerException catch (e) {
      if (e.statusCode == 401 || e.statusCode == 403) {
        return Left(AuthFailure(e.message));
      }
      if (e.statusCode == 503) {
        return const Left(ServerFailure('Memory engine is not configured.'));
      }
      return Left(ServerFailure(e.message, errorCode: e.errorCode));
    } on DioException {
      return const Left(NetworkFailure());
    } on Exception {
      return const Left(UnexpectedFailure());
    }
  }
}
