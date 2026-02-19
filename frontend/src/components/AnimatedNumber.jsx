/**
 * AnimatedNumber.jsx — Smoothly animating counter using framer-motion.
 */

import { useEffect, useRef } from 'react';
import { motion, useSpring, useTransform } from 'framer-motion';

export default function AnimatedNumber({ value, decimals = 1, className = '' }) {
  const spring = useSpring(0, { stiffness: 80, damping: 20 });
  const display = useTransform(spring, (v) => v.toFixed(decimals));
  const ref = useRef(null);

  useEffect(() => {
    spring.set(value);
  }, [value, spring]);

  useEffect(() => {
    const unsubscribe = display.on('change', (v) => {
      if (ref.current) ref.current.textContent = v;
    });
    return unsubscribe;
  }, [display]);

  return <motion.span ref={ref} className={className}>{value.toFixed(decimals)}</motion.span>;
}
