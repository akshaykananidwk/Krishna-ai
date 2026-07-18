import '../domain/entities/memory.dart';

class MemoryModel extends Memory {
  const MemoryModel({
    required super.id,
    required super.sourceType,
    required super.content,
    required super.pinned,
    required super.createdAt,
    super.title,
    super.tags,
  });

  factory MemoryModel.fromJson(Map<String, dynamic> json) => MemoryModel(
        id: json['id'] as String,
        sourceType: json['source_type'] as String,
        content: json['content'] as String,
        pinned: json['pinned'] as bool? ?? false,
        createdAt: DateTime.parse(json['created_at'] as String),
        title: json['title'] as String?,
        tags: (json['tags'] as List<dynamic>? ?? [])
            .map((e) => e as String)
            .toList(),
      );
}

class MemorySearchHitModel extends MemorySearchHit {
  const MemorySearchHitModel({
    required super.memory,
    required super.score,
    required super.similarity,
  });

  factory MemorySearchHitModel.fromJson(Map<String, dynamic> json) =>
      MemorySearchHitModel(
        memory: MemoryModel.fromJson(json['memory'] as Map<String, dynamic>),
        score: (json['score'] as num).toDouble(),
        similarity: (json['similarity'] as num).toDouble(),
      );
}
