import 'package:equatable/equatable.dart';

import 'chat_message.dart';

/// Lightweight conversation summary shown in the conversation list.
class Conversation extends Equatable {
  const Conversation({
    required this.id,
    required this.title,
    required this.createdAt,
    this.lastMessageAt,
  });

  final String id;
  final String title;
  final DateTime createdAt;
  final DateTime? lastMessageAt;

  @override
  List<Object?> get props => [id, title, createdAt, lastMessageAt];
}

/// A conversation together with its full message history.
class ConversationDetail extends Conversation {
  const ConversationDetail({
    required super.id,
    required super.title,
    required super.createdAt,
    required this.messages,
    super.lastMessageAt,
  });

  final List<ChatMessage> messages;

  @override
  List<Object?> get props => [...super.props, messages];
}

/// Events emitted while an assistant reply streams in.
sealed class ChatStreamEvent {
  const ChatStreamEvent();
}

class ChatDelta extends ChatStreamEvent {
  const ChatDelta(this.text);
  final String text;
}

class ChatDone extends ChatStreamEvent {
  const ChatDone({required this.messageId, required this.content});
  final String messageId;
  final String content;
}

class ChatStreamError extends ChatStreamEvent {
  const ChatStreamError(this.detail);
  final String detail;
}
