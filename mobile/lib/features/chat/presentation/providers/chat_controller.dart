import 'package:equatable/equatable.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/chat_message.dart';
import '../../domain/entities/conversation.dart';
import 'chat_providers.dart';

/// UI state for a single open conversation.
class ChatState extends Equatable {
  const ChatState({
    this.messages = const [],
    this.isLoading = true,
    this.isSending = false,
    this.error,
  });

  final List<ChatMessage> messages;
  final bool isLoading;
  final bool isSending;
  final String? error;

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? isLoading,
    bool? isSending,
    String? error,
    bool clearError = false,
  }) =>
      ChatState(
        messages: messages ?? this.messages,
        isLoading: isLoading ?? this.isLoading,
        isSending: isSending ?? this.isSending,
        error: clearError ? null : (error ?? this.error),
      );

  @override
  List<Object?> get props => [messages, isLoading, isSending, error];
}

/// Drives one conversation: initial load plus streamed sends.
class ChatController extends StateNotifier<ChatState> {
  ChatController(this._ref, this._conversationId) : super(const ChatState()) {
    _load();
  }

  final Ref _ref;
  final String _conversationId;

  Future<void> _load() async {
    final result =
        await _ref.read(chatRepositoryProvider).getConversation(_conversationId);
    state = result.fold(
      (failure) => state.copyWith(isLoading: false, error: failure.message),
      (detail) => state.copyWith(isLoading: false, messages: detail.messages),
    );
  }

  Future<void> send(String content) async {
    if (state.isSending || content.trim().isEmpty) return;

    final now = DateTime.now();
    final userMessage = ChatMessage(
      id: 'local-user-${now.microsecondsSinceEpoch}',
      role: MessageRole.user,
      content: content.trim(),
      createdAt: now,
    );
    final assistantId = 'local-assistant-${now.microsecondsSinceEpoch}';
    final assistantMessage = ChatMessage(
      id: assistantId,
      role: MessageRole.assistant,
      content: '',
      createdAt: now,
      isStreaming: true,
    );

    state = state.copyWith(
      messages: [...state.messages, userMessage, assistantMessage],
      isSending: true,
      clearError: true,
    );

    final stream = _ref.read(chatRepositoryProvider).sendMessage(
          conversationId: _conversationId,
          content: content.trim(),
        );

    final buffer = StringBuffer();
    await for (final event in stream) {
      switch (event) {
        case ChatDelta(:final text):
          buffer.write(text);
          _updateAssistant(assistantId, buffer.toString(), streaming: true);
        case ChatDone(:final content):
          _updateAssistant(assistantId, content, streaming: false);
        case ChatStreamError(:final detail):
          _updateAssistant(
            assistantId,
            buffer.isEmpty ? '⚠️ $detail' : buffer.toString(),
            streaming: false,
          );
          state = state.copyWith(error: detail);
      }
    }

    state = state.copyWith(isSending: false);
  }

  void _updateAssistant(String id, String content, {required bool streaming}) {
    state = state.copyWith(
      messages: [
        for (final m in state.messages)
          if (m.id == id)
            m.copyWith(content: content, isStreaming: streaming)
          else
            m,
      ],
    );
  }
}

final chatControllerProvider =
    StateNotifierProvider.autoDispose.family<ChatController, ChatState, String>(
  (ref, conversationId) => ChatController(ref, conversationId),
);
