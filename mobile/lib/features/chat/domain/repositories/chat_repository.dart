import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/conversation.dart';

/// Contract for the AI Chat feature.
abstract interface class ChatRepository {
  Future<Either<Failure, List<Conversation>>> listConversations();

  Future<Either<Failure, Conversation>> createConversation({String? title});

  Future<Either<Failure, ConversationDetail>> getConversation(String id);

  Future<Either<Failure, Conversation>> renameConversation(
    String id,
    String title,
  );

  Future<Either<Failure, Unit>> deleteConversation(String id);

  /// Streams the assistant reply for [content]. The stream emits [ChatDelta]s
  /// as text arrives and terminates with a [ChatDone] or [ChatStreamError].
  Stream<ChatStreamEvent> sendMessage({
    required String conversationId,
    required String content,
  });
}
