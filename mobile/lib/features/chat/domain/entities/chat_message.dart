import 'package:equatable/equatable.dart';

enum MessageRole { user, assistant, system }

/// A single message within a conversation.
class ChatMessage extends Equatable {
  const ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.createdAt,
    this.isStreaming = false,
  });

  final String id;
  final MessageRole role;
  final String content;
  final DateTime createdAt;

  /// True while the assistant reply is still being streamed in.
  final bool isStreaming;

  bool get isUser => role == MessageRole.user;

  ChatMessage copyWith({String? content, bool? isStreaming}) => ChatMessage(
        id: id,
        role: role,
        content: content ?? this.content,
        createdAt: createdAt,
        isStreaming: isStreaming ?? this.isStreaming,
      );

  @override
  List<Object?> get props => [id, role, content, createdAt, isStreaming];
}
