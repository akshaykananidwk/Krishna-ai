import 'package:dartz/dartz.dart';
import 'package:dio/dio.dart';

import '../../../../core/error/exceptions.dart';
import '../../../../core/error/failures.dart';
import '../../domain/entities/conversation.dart';
import '../../domain/repositories/chat_repository.dart';
import '../datasources/chat_remote_data_source.dart';

class ChatRepositoryImpl implements ChatRepository {
  const ChatRepositoryImpl(this._remote);
  final ChatRemoteDataSource _remote;

  @override
  Future<Either<Failure, List<Conversation>>> listConversations() =>
      _guard(() => _remote.listConversations());

  @override
  Future<Either<Failure, Conversation>> createConversation({String? title}) =>
      _guard(() => _remote.createConversation(title: title));

  @override
  Future<Either<Failure, ConversationDetail>> getConversation(String id) =>
      _guard(() => _remote.getConversation(id));

  @override
  Future<Either<Failure, Conversation>> renameConversation(
    String id,
    String title,
  ) =>
      _guard(() => _remote.renameConversation(id, title));

  @override
  Future<Either<Failure, Unit>> deleteConversation(String id) => _guard(() async {
        await _remote.deleteConversation(id);
        return unit;
      });

  @override
  Stream<ChatStreamEvent> sendMessage({
    required String conversationId,
    required String content,
  }) async* {
    try {
      yield* _remote.sendMessage(
        conversationId: conversationId,
        content: content,
      );
    } on DioException {
      yield const ChatStreamError('Network error. Please try again.');
    } on ServerException catch (e) {
      yield ChatStreamError(e.message);
    }
  }

  Future<Either<Failure, T>> _guard<T>(Future<T> Function() call) async {
    try {
      return Right(await call());
    } on ServerException catch (e) {
      if (e.statusCode == 404) return const Left(ServerFailure('Not found.'));
      if (e.statusCode == 401 || e.statusCode == 403) {
        return Left(AuthFailure(e.message));
      }
      if (e.statusCode == 503) {
        return const Left(
          ServerFailure('AI is not configured on the server yet.'),
        );
      }
      return Left(ServerFailure(e.message, errorCode: e.errorCode));
    } on DioException {
      return const Left(NetworkFailure());
    } on Exception {
      return const Left(UnexpectedFailure());
    }
  }
}
