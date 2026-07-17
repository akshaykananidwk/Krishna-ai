import '../../domain/entities/chat_message.dart';
import '../../domain/entities/conversation.dart';

MessageRole _roleFromString(String value) => switch (value) {
      'assistant' => MessageRole.assistant,
      'system' => MessageRole.system,
      _ => MessageRole.user,
    };

class ChatMessageModel extends ChatMessage {
  const ChatMessageModel({
    required super.id,
    required super.role,
    required super.content,
    required super.createdAt,
  });

  factory ChatMessageModel.fromJson(Map<String, dynamic> json) =>
      ChatMessageModel(
        id: json['id'] as String,
        role: _roleFromString(json['role'] as String),
        content: json['content'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
      );
}

class ConversationModel extends Conversation {
  const ConversationModel({
    required super.id,
    required super.title,
    required super.createdAt,
    super.lastMessageAt,
  });

  factory ConversationModel.fromJson(Map<String, dynamic> json) =>
      ConversationModel(
        id: json['id'] as String,
        title: json['title'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
        lastMessageAt: json['last_message_at'] != null
            ? DateTime.parse(json['last_message_at'] as String)
            : null,
      );
}

class ConversationDetailModel extends ConversationDetail {
  const ConversationDetailModel({
    required super.id,
    required super.title,
    required super.createdAt,
    required super.messages,
    super.lastMessageAt,
  });

  factory ConversationDetailModel.fromJson(Map<String, dynamic> json) =>
      ConversationDetailModel(
        id: json['id'] as String,
        title: json['title'] as String,
        createdAt: DateTime.parse(json['created_at'] as String),
        lastMessageAt: json['last_message_at'] != null
            ? DateTime.parse(json['last_message_at'] as String)
            : null,
        messages: (json['messages'] as List<dynamic>)
            .map((e) => ChatMessageModel.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
