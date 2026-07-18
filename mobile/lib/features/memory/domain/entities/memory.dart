import 'package:equatable/equatable.dart';

/// A unit of remembered knowledge from the Memory Engine.
class Memory extends Equatable {
  const Memory({
    required this.id,
    required this.sourceType,
    required this.content,
    required this.pinned,
    required this.createdAt,
    this.title,
    this.tags = const [],
  });

  final String id;
  final String sourceType;
  final String content;
  final bool pinned;
  final DateTime createdAt;
  final String? title;
  final List<String> tags;

  @override
  List<Object?> get props => [id, sourceType, content, pinned, createdAt, title, tags];
}

/// A ranked memory returned from semantic search.
class MemorySearchHit extends Equatable {
  const MemorySearchHit({
    required this.memory,
    required this.score,
    required this.similarity,
  });

  final Memory memory;
  final double score;
  final double similarity;

  @override
  List<Object?> get props => [memory, score, similarity];
}
