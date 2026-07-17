/// Client-side form validators. These mirror the backend rules so users get
/// instant feedback; the server remains the source of truth.
class Validators {
  const Validators._();

  static final _emailRegex = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

  static String? email(String? value) {
    final v = value?.trim() ?? '';
    if (v.isEmpty) return 'Email is required.';
    if (!_emailRegex.hasMatch(v)) return 'Enter a valid email address.';
    return null;
  }

  static String? password(String? value) {
    final v = value ?? '';
    if (v.isEmpty) return 'Password is required.';
    if (v.length < 8) return 'At least 8 characters.';
    if (!v.contains(RegExp('[a-z]'))) return 'Add a lowercase letter.';
    if (!v.contains(RegExp('[A-Z]'))) return 'Add an uppercase letter.';
    if (!v.contains(RegExp('[0-9]'))) return 'Add a digit.';
    return null;
  }

  static String? loginPassword(String? value) {
    if ((value ?? '').isEmpty) return 'Password is required.';
    return null;
  }

  static String? Function(String?) confirmPassword(String Function() other) {
    return (String? value) {
      if (value != other()) return 'Passwords do not match.';
      return null;
    };
  }
}
