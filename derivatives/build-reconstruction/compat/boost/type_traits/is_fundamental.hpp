#pragma once
// Minimal stand-in for boost/type_traits/is_fundamental.hpp (Boost 1.3x era).
// serialize.h uses exactly three names from it; C++11 <type_traits> supplies them.
// This lets the ORIGINAL serialize.h parse without a full Boost install, WITHOUT
// editing the original source. NOT money.
#include <type_traits>
namespace boost {
  template <class T> struct is_fundamental : std::is_fundamental<T> {};
  typedef std::true_type  true_type;
  typedef std::false_type false_type;
}
