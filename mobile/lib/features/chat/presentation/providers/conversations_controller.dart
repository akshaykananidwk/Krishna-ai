import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/entities/conversation.dart';
import 'chat_providers.dart';

/// Loads and mutates the list of the user's conversations.
class ConversationsController
    extends StateNotifier<AsyncValue<List<Conversation>>> {
  ConversationsController(this._ref) : super(const AsyncValue.loading()) {
    load();
  }

  final Ref _ref;

  Future<void> load() async {
    state = const AsyncValue.loading();
    final result = await _ref.read(chatRepositoryProvider).listConversations();
    state = result.fold(
      (failure) => AsyncValue.error(failure.message, StackTrace.current),
      (conversations) => AsyncValue.data(conversations),
    );
  }

  /// Creates a new conversation and returns it, or null on failure.
  Future<Conversation?> create() async {
    final result =
        await _ref.read(chatRepositoryProvider).createConversation();
    return result.fold((_) => null, (conversation) {
      state = state.whenData((list) => [conversation, ...list]);
      return conversation;
    });
  }

  Future<void> delete(String id) async {
    final result =
        await _ref.read(chatRepositoryProvider).deleteConversation(id);
    result.fold((_) {}, (_) {
      state = state.whenData(
        (list) => list.where((c) => c.id != id).toList(),
      );
    });
  }
}

final conversationsControllerProvider = StateNotifierProvider<
    ConversationsController, AsyncValue<List<Conversation>>>((ref) {
  return ConversationsController(ref);
});
